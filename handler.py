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

def buildNREvent(ccEvent):
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
  # drop unwanted attributes and nested objects since NR Events API ignores them anyway
  drop = {'accountId', 'attributes', 'relationships', 'type', 'extradata', 'extradataHash'}
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

def handleScheduledEvent(event):
  import os
  from newrelic_telemetry_sdk import Event, EventClient
  import math
  import requests
  CC_REGION = 'us-west-2'
  CC_ACCOUNTIDS = 'BVyTCW0Va'
  CC_APIKEY = os.environ["CLOUD_CONFORMITY_API_KEY"]
  CC_PAGE_SIZE = 1000
  CC_REGIONS = ['global', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-2',
'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-east-1', 'ca-central-1', 'eu-central-1', 'eu-west-1',
'eu-west-2', 'eu-west-3', 'eu-north-1', 'eu-south-1', 'me-south-1', 'sa-east-1', 'af-south-1']
  url = (
      "https://"
      + CC_REGION
      + "-api.cloudconformity.com/v1/checks"
      
  )
  print('hello')
  print('url', url)
  headers = {
      "Content-Type": "application/vnd.api+json",
      "Authorization": "ApiKey " + CC_APIKEY,
  }
  checks = []
  for region in CC_REGIONS:
    response = requests.get(url, headers=headers, params='accountIds='+ CC_ACCOUNTIDS + '&filter[regions]=' + region + '&page[size]=' + str(CC_PAGE_SIZE))
    
    response.raise_for_status()
    response_json = response.json().get('data')
    checks.extend(response_json)
    total_records = response.json().get('meta').get('total')
    total_pages = math.ceil(total_records/CC_PAGE_SIZE)
    print('region', region)
    print('total records', total_records)
    print('total pages', total_pages)
    for page in range(1, total_pages):
      res = requests.get(url, headers=headers, params='accountIds='+ CC_ACCOUNTIDS + '&filter[regions]=' + region + '&page[size]=' + str(CC_PAGE_SIZE) + '&page[number]=' + str(page))
      res.raise_for_status()
      res_json = res.json().get('data')
      checks.extend(res_json)
    print('checks so far', len(checks))
  data = json.dumps(checks)
  print('response', len(checks), data)
  event_client = EventClient(os.environ["NEW_RELIC_INSERT_KEY"])
  # convert to NR events
  nrEvents = list(map(lambda c: buildNREvent(c), checks))
  print('NR Events to be sent', json.dumps(nrEvents))
  # batch events
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
    if event.get('source') == 'aws.events':
      nrEvents = handleScheduledEvent(event)
      print('sent all {} events!'.format(len(nrEvents)))
      return {
          "message": "{} Events posted to your New Relic account successfully!".format(len(nrEvents))
      }
    else:
      # Get the object from the event and show its content type
      bucket = event['Records'][0]['s3']['bucket']['name']
      key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
      try:
          res = s3.get_object(Bucket=bucket, Key=key)
          body = res['Body'].read().decode('utf-8')
      except Exception as e:
          print(e)
          print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
          raise e
      # build custom event object
      ccEvent = json.loads(body)[0]  # CC event objects are always an array of size 1
      nrEvent = buildNREvent(ccEvent)
      print('Sending NR event', nrEvent)
      event_client = EventClient(os.environ["NEW_RELIC_INSERT_KEY"])
      response = event_client.send(nrEvent)
      response.raise_for_status()
      print("Event sent successfully!", nrEvent)

      # Use this code if you don't use the http event with the LAMBDA-PROXY
      # integration
      
      return {
          "message": "Event posted to your New Relic account successfully!",
          "event": nrEvent
      }
