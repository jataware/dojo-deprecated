import argparse
import json

import requests


def get_mapper(dojo_url, model_id):
    ofs = requests.get(f"{dojo_url}/dojo/outputfile/{model_id}").json()
    for of in ofs:
        mapper = of["transform"]
        with open(f'/mappers/mapper_{of["id"]}.json', "w") as f:
            f.write(json.dumps(mapper))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mapper")
    parser.add_argument("dojo_url", help="dojo_url")
    parser.add_argument("model_id", help="model_id")
    args = parser.parse_args()
    get_mapper(args.dojo_url, args.model_id)
