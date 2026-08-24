# Basic OTA Campaign API Take-Home

## Overview

Build a small REST API for managing over-the-air (OTA) software update campaigns for vehicles.

This exercise is intended for an entry-level software engineer. We are looking for clear, working code and sensible decisions. You do not need prior automotive experience.

## Time Budget

Spend **4 to 8 hours**. Stop after 8 hours, even if the solution is not complete. In your `README.md`, note any unfinished work and what you would do next.

## What to Build

Your API should manage vehicles and OTA campaigns.

A vehicle has:

```json
{
  "vin": "1FTFW1E89PFA12345",
  "model": "F150",
  "software_version": "4.2.1",
  "feature_codes": [
    "GMR0M",
    "K4Q5H",
    "6F5QO",
    "B7STG",
    "9BN04",
    "NHT6M",
    "4160R",
    "2HA9P",
    "RCLX3",
    "Y8YZ3",
    "SB9OE",
    "6EU0O",
    "HZD8D",
    "9SZCR",
    "51ALG",
    "8T2ST",
    "G5HC9",
    "O5L8P",
    "Y7LH7",
    "87D08"
  ]
}
```

An OTA campaign has:

```json
{
  "id": "campaign-1",
  "name": "Summer software update",
  "target_version": "4.3.0",
  "target_feature_codes": ["B7STG"],
  "vehicle_vins": [
    "1FTFW1E89PFA12345",
    "1FTFW1E89PFA12346",
    "1FTFW1E89PFA12347",
    "1FTFW1E89PFA12348"
  ]
}
```

Feature codes are exactly five characters and contain only uppercase letters
and digits, with at least one of each. When a campaign is created with
`target_feature_codes`, assign every vehicle containing at least one of those
codes to the campaign. Feature codes may be shared by multiple vehicles.

The provided data contains 25 vehicles across eight models. Every vehicle has
20 feature codes:

- Any two vehicles of the same model share exactly 16 codes (80%).
- Any two vehicles of different models share exactly 3 codes (15%).
- The remaining 4 codes are unique to each vehicle.

For example, targeting `["B7STG"]` assigns all four F150 vehicles. Directly
adding a vehicle through the vehicle assignment endpoint remains supported and
does not require the vehicle to match the campaign's target feature codes.

Implement these endpoints:

| Method | Endpoint                   | Behavior                    |
| ------ | -------------------------- | --------------------------- |
| `GET`  | `/vehicles`                | List all vehicles           |
| `GET`  | `/campaigns`               | List all campaigns          |
| `GET`  | `/campaigns/{id}`          | Get one campaign            |
| `POST` | `/campaigns`               | Create a campaign           |
| `POST` | `/campaigns/{id}/vehicles` | Add a vehicle to a campaign |

For `POST /campaigns/{id}/vehicles`, accept:

```json
{
  "vin": "1FTFW1E89PFA12345"
}
```

## Requirements

- Use Python, TypeScript/JavaScript, Go, Java, or C#.
- Use PostgreSQL to store vehicles, campaigns, and campaign-to-vehicle assignments.
- Store vehicle feature codes and each campaign's target feature codes in PostgreSQL.
- PostgreSQL must run in Docker using a `docker-compose.yml` file.
- The API may run locally on your machine or in Docker. A `Dockerfile` for the API is not required.
- Document the commands for starting PostgreSQL and the API in `README.md`.
- Load the starting vehicles and their feature codes from `data/vehicles.json` into PostgreSQL. Seeding should be safe to run more than once without creating duplicate vehicles or duplicate vehicle-to-feature-code associations.
- Store database connection settings in environment variables. Do not commit passwords or other secrets.
- Return JSON responses and appropriate HTTP status codes.
- Require non-empty string values for `id`, `name`, and `target_version` when creating a campaign.
- `POST /campaigns` may accept `target_feature_codes` as an optional array. If it is omitted or empty, create the campaign without automatically assigning vehicles.
- Each target feature code must be five characters, contain at least one uppercase letter and one digit, contain no other characters, and exist on at least one vehicle. Reject the entire request without creating a campaign if any supplied code is invalid or unknown.
- Duplicate target feature codes must not create duplicate target-code records or vehicle assignments.
- A campaign created with multiple target feature codes must include vehicles matching any supplied code.
- Vehicle responses must include `feature_codes`. Campaign responses must include `target_feature_codes` and the complete `vehicle_vins` list.
- Return `404 Not Found` when a requested campaign or vehicle does not exist.
- Return a clear client error when a campaign ID already exists.
- Return a clear client error for malformed or unknown target feature codes.
- Do not add the same vehicle to a campaign more than once, including when the vehicle was already assigned through feature-code targeting.
- Add automated tests for the main success and error cases.
- Include setup, run, test, and example request instructions in `README.md`.

You may use any open-source framework or library. No paid services or API keys are needed.

## Example Requests

Create a campaign:

```http
POST /campaigns
Content-Type: application/json

{
  "id": "campaign-1",
  "name": "Summer software update",
  "target_version": "4.3.0",
  "target_feature_codes": ["B7STG"]
}
```

A successful response should use status `201 Created` and include the new
campaign and all four F150 VINs selected by the shared `B7STG` feature code.

Add a vehicle to the campaign:

```http
POST /campaigns/campaign-1/vehicles
Content-Type: application/json

{
  "vin": "1FTFW1E89PFA12345"
}
```

## What to Submit

- The working API and automated tests.
- A `README.md` with setup, run, test, and example request instructions.
- A note in the `README.md` with time spent, assumptions, known gaps, and next steps.
- Publish the submission in a public GitHub repository with a generic, non-identifying repository name, and share the repository URL with us.

We do not expect production infrastructure, advanced OTA rules, authentication, a user interface, or a perfect solution.

## Optional Improvements

Only attempt these after completing the required API:

- Update or delete a campaign.
- Remove a vehicle from a campaign.
- Add simple campaign statuses such as `DRAFT` and `ACTIVE`.
- Add OpenAPI or Swagger documentation.
- Add linting or continuous integration.
