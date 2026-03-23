# Examon API Documentation

## Base URL

http://172.16.47.112:5000/api/v1

## Authentication

The authentication method is basic auth, using the provided username and password.

## Endpoint: POST /examon/jobs/query

This endpoint is used to query job information in the ExaMon system. The job information are stored in a table having the schema of the SLURM [job response API](https://slurm.schedmd.com/archive/slurm-22.05.10/rest_api.html#v0.0.38_job_response_properties) corresponding to the appropriate SLURM version. 
In addition to the standard SLURM job properties, ExaMon adds the `energy` column to the table. It is a stringified JSON object with the following properties:

- `job_id`: The ID of the job.
- `data_quality_(%)`: The data quality as a percentage.
- `version`: The version of the energy schema.
- `total_energy_consumption`: The total energy consumption for the job.
- `message`: A message about the data quality and score.
- `unit`: The unit of the energy consumption, such as "Wh".

This endpoint supports pagination. To handle large tables, it is possible to define the time window, using the `tstart` and `tstop` properties, in order to limit the amount of data for each request.

### Request

The request should be a JSON object with the following properties:

- `tags`: An object where each key is a tag name and the value is an array of tag values. For example, to filter by job_id, you would include `"tags": {"job_id": ["5296"]}`.
- `time_zone`: A string representing the time zone, such as "Europe/Rome".
- `aggrby`: This field is currently not used and should be set to null.
- `metrics`: An array of strings representing the job table name, such as `["job_info_E4red"]`.
- `limit`: Limits the number of rows in the table to a given value.
- `tstart`: A number representing the initial bound of the time window used to filter the data in milliseconds since the Unix epoch - Mandatory.
- `tstop`: A number representing the final bound of the time window used to filter the data in milliseconds since the Unix epoch - Optional.
- `groupby`: An array of objects, each with a `name` and `tags` property. The `name` should be "tag" and the `tags` should be an array of strings representing the selected column in the table. Use `"*"` as wildcard to select all columns of the table.

### Response

The response will be a serialized Pandas Dataframe in the `records` format, a collection of table rows, where each row is an array of `{Column_Name: Value}` objects. The columns returned are the ones specified in the `groupby` field of the request.
The response will be a JSON array of objects. Each object will have a key for each tag specified in the `groupby` field of the request. 

### Example

In this example, we query for the `energy` column of the job table `job_info_E4red` corresponding to the job_id `5326`.


Request:

```json
{
    "tags": {
        "job_id": ["5326"]
    },
    "time_zone": "Europe/Rome",
    "aggrby": null,
    "metrics": ["job_info_E4red"],
    "limit": null,
    "tstart": 1000,
    "tstop": null,
    "groupby": [
        {
            "name": "tag",
            "tags": ["energy"]
        }
    ]
}
```


Response:

```json
[
    {
        "energy": "{\"job_id\": 5326, \"data_quality_(%)\": 100, \"version\": \"v0.1\", \"total_energy_consumption\": 6.388100000752343, \"message\": \"Missing nodes (%): 0.000000; Quality score (%): 100.000000; \", \"unit\": \"Wh\"}"
    }
]
```

Notes:

- In this example we filter by job_id so to extend the db search to the full table is suggested to use a low value (>0) for the mandatory tstart property. 


Example

This is a full example using the Python lunguage.

```python
import requests
from requests.auth import HTTPBasicAuth

# Endpoint
api_url = 'http://172.16.47.112:5000/api/v1/examon/jobs/query'

# Replace these values with your actual username, and password
username = ''
password = ''

# JSON data to be sent in the request body
data = {
    "tags": {
        "job_id": [
            "5326"
        ]
    },
    "time_zone": "Europe/Rome",
    "aggrby": None,
    "metrics": [
        "job_info_E4red"
    ],
    "limit": None,
    "tstart": 1000,
    "tstop": None,
    "groupby": [
        {
            "name": "tag",
            "tags": [
                "energy"
            ]
        }
    ]
}

headers = {
    'Content-Type': 'application/json',
    'Accept-Encoding': 'gzip, deflate'
}

# the payload should be encoded as follow:
json_data = json.dumps(json.dumps(data)).encode("utf-8")

# Set up basic authentication
auth = HTTPBasicAuth(username, password)

# Send POST request with JSON content and basic authentication
response = requests.post(api_url, data=json_data, auth=auth, headers=headers)

# Check the response status code
if response.status_code == 200:
    print("Request successful. Response:")
    print(response.json())
else:
    print(f"Request failed with status code {response.status_code}. Response content:")
    print(response.text)
```

Response:

```
Request successful. Response:
[{"energy":"{\"job_id\": 5326, \"data_quality_(%)\": 100, \"version\": \"v0.1\", \"total_energy_consumption\": 6.388100000752343, \"message\": \"Missing nodes (%): 0.000000; Quality score (%): 100.000000; \", \"unit\": \"Wh\"}"}]
```