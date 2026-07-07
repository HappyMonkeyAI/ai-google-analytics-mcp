# Google Analytics GA4 Service Account Setup Guide

This guide explains how to configure Google Cloud and Google Analytics 4 (GA4) so a service-account-based tool, such as a local AI or MCP agent, can authenticate and manage GA4 configuration through the Google Analytics Admin API.[cite:2][cite:5]

## Prerequisites

Before starting, make sure there is access to a Google account with administrative access to the target GA4 account or property, and permission to create or manage resources in a Google Cloud project.[cite:7][cite:19]

## 1. Create or select a Google Cloud project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).[cite:19]
2. Use the project selector at the top of the page to either choose an existing project or create a new one.[cite:19][cite:35]
3. Keep all later setup steps in the same Google Cloud project to avoid mismatched credentials and API settings.[cite:35]

## 2. Enable the required Google Analytics APIs

1. In Google Cloud Console, open **APIs & Services → Library**.[cite:19][cite:5]
2. Search for **Google Analytics Admin API** and click **Enable**.[cite:2][cite:5]
3. If the tool also needs to read analytics reporting data, enable **Google Analytics Data API** as well.[cite:4][cite:5]

The Admin API is used for configuration tasks such as working with GA4 accounts, properties, and related admin resources.[cite:2]

## 3. Create a service account

1. In Google Cloud Console, go to **IAM & Admin → Service Accounts**.[cite:9][cite:35]
2. Click **Create service account**.[cite:9][cite:35]
3. Enter a descriptive name such as `ga4-agent` and an optional description for the integration.[cite:9]
4. Click **Create and continue**.[cite:9]
5. On the optional permissions step, assign only the minimum Google Cloud IAM roles needed for the wider project, or skip project roles if the tool only needs GA4 access managed inside Analytics.[cite:15][cite:35]
6. Finish the creation flow and confirm the service account appears in the list.[cite:9][cite:35]

The new service account will have an email address in the form `name@project-id.iam.gserviceaccount.com`.[cite:9][cite:35]

## 4. Generate and download a JSON key

1. Open the newly created service account from the Service Accounts list.[cite:9][cite:11]
2. Go to the **Keys** tab.[cite:9][cite:11]
3. Select **Add key → Create new key**.[cite:9][cite:11]
4. Choose **JSON** and confirm the key creation.[cite:9][cite:11]
5. Save the downloaded `.json` key file in a secure location on the local machine.[cite:11][cite:33]

A common local convention is to place the file in a user-only config directory and lock down its permissions:

```bash
mkdir -p ~/.config/ga4
mv ~/Downloads/<downloaded-key>.json ~/.config/ga4/ga4-agent.json
chmod 600 ~/.config/ga4/ga4-agent.json
```

The JSON key should never be committed to source control or shared publicly because it allows authentication as the service account.[cite:11][cite:33]

## 5. Grant access inside Google Analytics 4

Google Cloud IAM is not enough on its own. The service account must also be added directly in Google Analytics access management so the Analytics APIs can authorize it for GA4 resources.[cite:7][cite:9][cite:15]

1. Open [Google Analytics](https://analytics.google.com/) and sign in.[cite:7][cite:31]
2. Click **Admin** in the lower-left corner.[cite:31][cite:32]
3. Under the relevant **Account** or **Property** column, open **Access management**.[cite:7][cite:31]
4. For tools that need to create properties, use **Account access management** rather than only property-level access.[cite:7][cite:15]
5. Click **Add users** and enter the full service account email address.[cite:9][cite:31]
6. Assign an appropriate role, such as **Editor** for standard read/write admin work, **Viewer** for read-only access, or **Administrator** only when full control is required.[cite:7][cite:9]
7. Save the changes.[cite:7]

## 6. Connect the key to the local tool

Most local tools that use Google service accounts support standard Application Default Credentials through the `GOOGLE_APPLICATION_CREDENTIALS` environment variable.[cite:5][cite:33]

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/ga4/ga4-agent.json"
```

Some tools instead ask for a direct `credentialsPath` or similar configuration value that points at the same JSON file.[cite:5][cite:33]

Example configuration:

```json
{
  "googleAnalytics": {
    "credentialsPath": "/home/user/.config/ga4/ga4-agent.json",
    "projectId": "your-project-id"
  }
}
```

## 7. Troubleshooting

- **Permission denied errors:** Confirm the Google Analytics Admin API is enabled and the service account has been added in GA4 access management with a sufficient role.[cite:2][cite:5][cite:7]
- **Can authenticate but cannot create properties:** Check that the service account was granted access at the GA4 account level, not only at the property level.[cite:7][cite:15]
- **Service account email rejected in GA4:** Verify the email was copied exactly from the Google Cloud service account page and that the correct GA4 account or property is selected in Admin.[cite:36][cite:37]
- **Security concerns:** Rotate or revoke old keys if they are exposed, and store active keys outside the repository in a protected local path.[cite:33][cite:35]

## Notes

This setup pattern is appropriate for service-account-based automation that needs to manage GA4 configuration from a local development machine or automation environment.[cite:2][cite:5] The exact runtime configuration depends on the tool being used, but the Google Cloud project, enabled API, service account JSON key, and GA4 access grant are the core requirements in all cases.[cite:5][cite:7][cite:33]
