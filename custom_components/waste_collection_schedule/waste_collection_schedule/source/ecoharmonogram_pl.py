import datetime
import requests
from collections import ChainMap
from dataclasses import dataclass
from functools import reduce
import operator
from typing import Dict, List

from waste_collection_schedule import Collection  # type: ignore[attr-defined]

TITLE: str = "Ecoharmonogram"
DESCRIPTION: str = "Source for Ecoharmonogram waste collection. Service is hosted on ecoharmonogram.pl."
URL: str = "https://ecoharmonogram.pl"

COMMUNITY_ID = "108"
TOWN_ID = "2149"

TEST_CASES = {
    "schedules": [
        {
            "month": 1,
            "days": "1;2;3;4;5",
            "year": "2021",
            "scheduleDescriptionId": "12345",
        }
    ],
    "scheduleDescription": [
        {
            "id": "24410",
            "month": "12",
            "days": "15",
            "year": "2021",
            "scheduleDescriptionId": "12345",
            "name": "LOREM IPSUM",
            "description": "Dolor sit amet",
        }
    ],
    "street": {"id": "1234567", "name": "Street name"},
    "town": {"name"},
    "schedulePeriod": {
        "startDate": "2021-01-01",
        "endDate": "2021-12-31",
        "changeDate": "2021-05-17 15:45:15",
    },
    "search": {"number": "123"},
}


class Source:
    def __init__(
        self, street_name, house_number, community_id=COMMUNITY_ID, town_id=TOWN_ID
    ):
        self.community_id = community_id
        self.town_id = town_id
        self.street_name = street_name
        self.house_number = house_number

    def fetch(self):
        API_URL = "https://pluginssl.ecoharmonogram.pl/api/v1/plugin/v1"
        schedule_period = requests.post(
            f"{API_URL}/schedulePeriodsWithDataForCommunity",
            f"communityId={self.community_id}",
        ).json()["schedulePeriods"][0]["id"]
        street_ids = requests.post(
            f"{API_URL}/streets",
            f"choosedStreetIds=&groupId=1&number=&schedulePeriodId={schedule_period}&streetName=&townId={self.town_id}",
        ).json()["streets"]
        street_id = next(
            filter(lambda x: x["name"].lower() == self.street_name.lower(), street_ids)
        )["id"]
        schedules_response = requests.post(
            f"{API_URL}/schedules", f"number={self.house_number}&streetId={street_id}"
        ).json()
        schedules_normalized = map(
            lambda schedule: mk_schedule(
                schedule, schedules_response["scheduleDescription"]
            ),
            schedules_response["schedules"],
        )
        return reduce(operator.iconcat, list(schedules_normalized), [])


def mk_schedule(schedule, schedule_descriptions):
    schedule_type = schedule_type_for(
        schedule_descriptions, schedule["scheduleDescriptionId"]
    )
    return list(
        map(
            lambda day: Collection(
                t=schedule_type["name"],
                date=datetime.date(
                    day=int(day),
                    month=int(schedule["month"]),
                    year=int(schedule["year"]),
                ),
                icon=schedule_type["icon"],
            ),
            schedule["days"].split(";"),
        )
    )


def schedule_type_for(schedule_descriptions, description_id):
    name = next(filter(lambda x: description_id == x["id"], schedule_descriptions))[
        "name"
    ]
    return {
        "name": name.lower(),
        "icon": schedule_types.get(name.lower(), "mdi:trash-can"),
    }


schedule_types = {
    "resztkowe": "mdi:trash-can",
    "bio": "mdi:recycle",
    "szkło": "mdi:bottle-soda-classic",
    "papier": "mdi:newspaper",
    "metale i tworzywa sztuczne": "mdi:factory",
}
