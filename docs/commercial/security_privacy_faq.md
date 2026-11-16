# Pilot Data and Security — Internal Response Guide

**Draft for internal use. Do not send this document as a security assurance or treat it as an approved customer FAQ.** The current repository does not establish production-grade account isolation, complete route authorization, formal retention guarantees, or a standard hosted deployment. Review each pilot's architecture, data, and written terms before accepting customer material.

## Where will a pilot's data be stored?

The application has local, S3, and Azure storage code paths, and local storage is the configured default. A provider implementation in the repository does not mean that provider is provisioned, tested, or approved for a particular pilot. Before receiving data, document the actual host, region, storage provider, access boundary, backups, and deletion process for that engagement. Do not promise on-premises, air-gapped, or region-specific handling without verifying the deployment.

## Who can access maps and API endpoints?

The backend has authentication components, but access control is not yet complete across all scene and asset routes, and per-customer scene isolation is not established. Do not claim that every API request is authenticated or that customer data is tenant-isolated. Until a pilot has a reviewed, isolated deployment and tested access policy, do not use shared multi-customer hosting for customer scene data.

The browser frontend can expose values configured as public client-side environment variables. Never put a confidential shared backend credential in a browser bundle or sample app.

## Are localization query images retained?

Retention and persistence behavior must be checked against the exact application version and deployment before a pilot. Do not promise that query images are not stored, are automatically deleted, or can be disabled without confirming the request path and storage behavior. Agree in writing whether query images may be collected, the purpose, access, retention period, and deletion method before capture or upload.

## Are external services used?

Review the specific deployment and workflow before answering. The Google 3D code is a separate synthetic-data research path; repository permission records restrict the documented use to internal research, benchmarking, and evaluation. Do not include Google 3D content in a customer deployment or commercial training claim unless applicable rights have been independently verified and recorded.

## How long is data retained, and how can it be deleted?

There is no approved, universal retention schedule in this document. Set the retention window and deletion responsibilities in the pilot agreement. Before promising deletion, verify which database rows, uploaded files, derived maps, backups, logs, and query images are covered, and confirm the process succeeds in the target deployment. Do not represent the existence of a cleanup route as proof that every copy is removed.

## Can we support a DPA, data residency, or compliance requirement?

Do not promise a DPA, regulatory compliance, a specific residency boundary, or an air-gapped deployment based on this repository. Escalate the customer's requirements for legal and engineering review before data is transferred. Do not use identifiable or sensitive personal data in an evaluation without an approved plan.

## Are API credentials scoped, revocable, and rotated?

The code includes API-key and JWT components, but scoped customer credential lifecycle and consistent route enforcement are not yet established. The current browser API-key configuration is public to users of the browser app. Do not describe it as a confidential customer credential, promise automatic rotation, or issue the same credential to multiple customers. Any pilot credential arrangement must be reviewed and documented for that deployment.

## Has the system been independently security tested?

No third-party security assessment or certification evidence is currently documented in this project pack. Do not claim a penetration test, SOC 2 certification, or other assurance unless separately completed and documented.

## Is traffic and stored data encrypted?

Encryption depends on the complete deployment, including the network edge, host, storage provider, and backup configuration. The application code alone does not establish end-to-end TLS or encryption at rest for a pilot. Verify these controls with the operator before making a customer commitment.

## Pilot preflight checklist

Before accepting customer data, record:

- Approved use case, area, capture permissions, and data types.
- Deployment owner, host, region, network exposure, and storage provider.
- Authentication mechanism and evidence that access is limited to the pilot team.
- Whether query images, video, maps, logs, and backups are stored.
- Retention period and verified deletion procedure for each data category.
- Required TLS and at-rest encryption controls and who operates them.
- Customer-approved support contacts and incident communication path.
- Written legal/security approvals required by the customer.

If a required item is unknown, mark it as an open blocker and do not make a guarantee or receive the affected data until it is resolved.
