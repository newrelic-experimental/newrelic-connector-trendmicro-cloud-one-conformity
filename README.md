[![New Relic Experimental header](https://github.com/newrelic/opensource-website/raw/master/src/images/categories/Experimental.png)](https://opensource.newrelic.com/oss-category/#new-relic-experimental)

# New Relic connector for Trend Micro Cloud One Conformity

>The project integrates [Trend Micro Cloud One Conformity](https://www.trendmicro.com/en_us/business/products/hybrid-cloud/cloud-one-conformity.html) ("Conformity") with [New Relic](https://newrelic.com/) when using the [AWS integration](https://www.cloudconformity.com/help/conformity-bot/aws-integration.html). The "solution" relies on [Amazon SNS](https://www.cloudconformity.com/help/communication/communication-channels/amazon-sns-communication.html) integration offered by Conformity. With this integration, you will complement your AWS observability by adding in Conformity monitoring, now using your New Relic account alongside all the telemetry for all your applications and services.

## Installation

> Make sure you have access to the following:
> * AWS account where you can deploy this solution.
> * Trend Micro Cloud One Conformity account that is linked with your AWS account.
> * New Relic account that is linked with your AWS account. If you don’t already have a New Relic account, you can sign up for a free account in the [AWS Marketplace](https://aws.amazon.com/marketplace/pp/B08L5FQMTG).

> Deploy [Conformity-to-S3](https://github.com/raphabot/Conformity-to-S3) solution to your AWS account before you deploy this solution. The quickest way to do so is by using this AWS CloudFormation [template](https://github.com/raphabot/Conformity-to-S3/releases/latest/download/ConformityToS3Stack.template.json).

> Be sure to add the necessary information to the  configuration file `config.dev.yml` in the project root directory. Replace the placeholders (in chevrons) with actual values. If you choose to fork this repository, do not commit this file as it holds sensitive information about your Trend Micro and New Relic accounts.

> Make sure you've set up [AWS Command Line Interface](https://aws.amazon.com/cli/) (AWS CLI) in your machine or build host from where you plan to deploy this solution.

> Make sure you've installed the latest version of `serverless` CLI.

> You need to have [Docker](https://docs.docker.com/install/) installed, along with [Python 3](https://www.python.org/downloads/).

> Initialize the node modules by running this command from the project root directory:
 `npm install`

> Deploy the solution using [serverless](https://www.serverless.com/framework/docs/getting-started/) CLI by running the following command. If you have [AWS CLI profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html) set up, include `–-profile <Profile Name>`.

> `sls deploy`

> This deploys the solution using the configuration defined in `config.dev.yml` file in the `us-east-1` Region of your AWS account, by default. You can specify the AWS account and Region by setting up your AWS CLI Profile on your machine or build host. You must deploy this solution in the same account and Region where you deployed the "Conformity-to-S3" solution.

## Getting Started
Refer to this [architecture diagram](architecture.png) for this solution's deployment architecture in your AWS environment.
Once the solution is deployed to your AWS account, you should start to see the custom event named `TMCloudOneConformityEvent` reported into your New Relic Dashboards and Data Explorer.

You can then build a [dashboard](new-relic-dashboard.png) in your New Relic account to keep tabs on your AWS account checks reported by Conformity.

## Support

New Relic hosts and moderates an online forum where customers can interact with New Relic employees as well as other customers to get help and share best practices.

## Contributing
We encourage your contributions to improve New Relic connector for Trend Micro Cloud One Conformity! Keep in mind when you submit your pull request, you'll need to sign the CLA via the click-through using CLA-Assistant. You only have to sign the CLA one time per project.
If you have any questions, or to execute our corporate CLA, required if your contribution is on behalf of a company,  please drop us an email at opensource@newrelic.com.

**A note about vulnerabilities**

As noted in our [security policy](../../security/policy), New Relic is committed to the privacy and security of our customers and their data. We believe that providing coordinated disclosure by security researchers and engaging with the security community are important means to achieve our security goals.

If you believe you have found a security vulnerability in this project or any of New Relic's products or websites, we welcome and greatly appreciate you reporting it to New Relic through [HackerOne](https://hackerone.com/newrelic).

## License
New Relic connector for Trend Micro Cloud One Conformity is licensed under the [Apache 2.0](http://apache.org/licenses/LICENSE-2.0.txt) License.
