import json
import urllib.parse
import boto3

s3 = boto3.client('s3')

def toCamelCase(kebabCasedStr):
  # saving first and rest using split() 
  first, *rest = kebabCasedStr.split('-')
  # the string is not hyphenated, return as-is
  if not rest:
    return kebabCasedStr
  # using map() to get all words other than 1st 
  # and titlecasing them 
  return ''.join([first.lower(), *map(str.title, rest)])

def keysToCamelCase(dict0):
  return {toCamelCase(k): v for k, v in dict0.items()}

def buildNREvent(ccEvent, accountIdMap=None, ruleIdCompliancesMap=None):
  from newrelic_telemetry_sdk import Event
  
  # flatten 'attributes' nested object (found in Checks API response)
  ccEvent = {**ccEvent, **ccEvent.get('attributes', {})}
  accountId = ccEvent.get('accountId', None)
  ruleId = ccEvent.get('ruleId', None)
  if accountId is None:
    # accountId can be found here in Checks API response
    accountId = ccEvent['relationships']['account']['data']['id']
  if ruleId is None:
    # ruleId can be found here in Checks API response
    ruleId = ccEvent['relationships']['rule']['data']['id']
    ccEvent.update({'ruleId': ruleId})
  # accountId is a reserved word in NR Events API
  ccEvent.update({'ccAccountId': accountId})
  compliances = ccEvent.get('compliances', None)
  if compliances is None:
    ccEvent.update({'compliances': ruleIdCompliancesMap.get(ruleId)})
  service = ccEvent.get('service', None)
  if service is None:
    ccEvent.update({'service': ccEvent['id'].split(':')[3]})
  cloudProviderId = ccEvent.get('cloudProviderId', None)
  if cloudProviderId is None:
    ccEvent.update({'cloudProviderId': accountIdMap.get(accountId)})
  # drop unwanted attributes and nested objects since NR Events API ignores them anyway
  drop = {'accountId', 'attributes', 'relationships', 'type', 'extradata', 'extradataHash', 'resolutionPageURL'}
  ccEvent = {k: v for k, v in ccEvent.items() if k not in drop}
  # convert kebab-cased keys to camel case (found in Checks API response)
  ccEvent = keysToCamelCase(ccEvent)
  # @see https://docs.newrelic.com/docs/telemetry-data-platform/ingest-manage-data/ingest-apis/use-event-api-report-custom-events#limits
  # reduce arrays into CSV string as NR Events API doesn't support arrays and maps as attribute values
  arrays = ['categories', 'compliances', 'tags']
  ccEvent.update({x: ','.join(ccEvent.get(x, [])) for x in arrays})
  
  nrEvent = Event(
      "TMCloudOneConformityEvent", ccEvent
  )
  return nrEvent

def makeCCRequest(url, params=''):
  import os
  import requests
  CC_REGION = 'us-west-2'
  CC_APIKEY = os.environ['CLOUD_CONFORMITY_API_KEY']
  url = (
      "https://"
      + CC_REGION
      + "-api.cloudconformity.com/v1/"
      + url
  )
  headers = {
      "Content-Type": "application/vnd.api+json",
      "Authorization": "ApiKey " + CC_APIKEY,
  }
  response = requests.get(url, headers=headers, params=params)
  response.raise_for_status()
  response_json = response.json()
  return response_json

def makeCCPublicRequest(url, params=''):
  import requests
  CC_REGION = 'us-west-2'
  url = (
      "https://"
      + CC_REGION
      + ".cloudconformity.com/v1/"
      + url
  )
  headers = {
      "Content-Type": "application/json"
  }
  response = requests.get(url, headers=headers, params=params)
  response.raise_for_status()
  response_json = response.json()
  return response_json

# handle event from the schedular
def handleScheduledEvent(event):
  import os
  from newrelic_telemetry_sdk import Event, EventClient
  import math

  # Fetch ruleId to compliances mapping using public "v1/services" endpoint
  url = 'services'
  response = makeCCPublicRequest(url)
  rules = response.get('included')
  awsRules = list(filter(lambda x: (x['type'] == 'rules' and x['attributes']['provider'] == 'aws'), rules))
  ruleIdCompliancesMap = {x['id']: x['attributes']['compliances'] for x in awsRules}

  # Fetch conformity account id to provider account id mapping using "v1/accounts" endpoint
  url = 'accounts'
  response = makeCCRequest(url)
  response_json = response.get('data')
  accountIdMap = {x['id']: x['attributes']['awsaccount-id'] for x in response_json}
  
  # Fetch all conformity checks for the account
  CC_ACCOUNTIDS = os.environ['CLOUD_CONFORMITY_ACCOUNT_ID']
  CC_PAGE_SIZE = 1000
  CC_REGIONS = ['global', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-2',
'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-east-1', 'ca-central-1', 'eu-central-1', 'eu-west-1',
'eu-west-2', 'eu-west-3', 'eu-north-1', 'eu-south-1', 'me-south-1', 'sa-east-1', 'af-south-1']
  url = 'checks'
  checks = []
  # Fetch checks by region, to get around the API limits
  # @see https://cloudone.trendmicro.com/docs/conformity/api-reference/#tag/Checks
  # There is a 10k limit to the maximum number of overall results that can be returned. 
  # Paging will not work for higher than this limit. 
  # To fetch larger numbers, segment your requests using account and region filtering. 
  # On larger accounts, filter requests per account, per region, per service.
  for region in CC_REGIONS:
    response = makeCCRequest(url, params='accountIds='+ CC_ACCOUNTIDS + '&filter[regions]=' + region + '&page[size]=' + str(CC_PAGE_SIZE))
    response_json = response.get('data')
    checks.extend(response_json)
    total_records = response.get('meta').get('total')
    total_pages = math.ceil(total_records/CC_PAGE_SIZE)
    print('region', region)
    print('total records', total_records)
    print('total pages', total_pages)
    for page in range(1, total_pages):
      res = makeCCRequest(url, params='accountIds='+ CC_ACCOUNTIDS + '&filter[regions]=' + region + '&page[size]=' + str(CC_PAGE_SIZE) + '&page[number]=' + str(page))
      res_json = res.get('data')
      checks.extend(res_json)
    print('checks so far', len(checks))

  data = json.dumps(checks)
  print('response', len(checks), data)
  # Transform checks into New Relic Telemetry SDK event payload
  nrEvents = list(map(lambda c: buildNREvent(c, accountIdMap, ruleIdCompliancesMap), checks))
  print('NR Events to be sent', json.dumps(nrEvents))
  # Batch events and send to New Relic
  event_client = EventClient(os.environ['NEW_RELIC_INSERT_KEY'])
  chunkSize = 1000
  chunks = [nrEvents[i:i + chunkSize] for i in range(0, len(nrEvents), chunkSize)]
  for idx, chunk in enumerate(chunks):
    response = event_client.send_batch(chunk)
    response.raise_for_status()
    print('sent chunk', idx)
  return nrEvents


def handler(event, context):
    import os
    import time
    from newrelic_telemetry_sdk import Event, EventClient

    print("Received event: " + json.dumps(event, indent=2))

    # check if it is a scheduled event from EventBridge
    if event.get('source') == 'aws.events' and event.get('detail-type') == 'Scheduled Event':
      nrEvents = handleScheduledEvent(event)
      print('sent all {} events!'.format(len(nrEvents)))
      return {
          "message": "{} Events posted to your New Relic account successfully!".format(len(nrEvents))
      }
    else:
      # Get the object (conformity check) from the S3 event
      bucket = event['Records'][0]['s3']['bucket']['name']
      key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
      try:
          res = s3.get_object(Bucket=bucket, Key=key)
          body = res['Body'].read().decode('utf-8')
      except Exception as e:
          print(e)
          print('Error getting object {} from bucket {}.'.format(key, bucket))
          raise e
      # Transform check into New Relic Telemetry SDK event payload
      # conformity check objects are always an array of size 1
      ccEvent = json.loads(body)[0]  
      nrEvent = buildNREvent(ccEvent)
      print('Sending NR event', nrEvent)
      event_client = EventClient(os.environ['NEW_RELIC_INSERT_KEY'])
      response = event_client.send(nrEvent)
      response.raise_for_status()
      print("Event sent successfully!", nrEvent)
      
      return {
          "message": "Event posted to your New Relic account successfully!",
          "event": nrEvent
      }
