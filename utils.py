import random
import json

def load_work_data():
    with open('commandphrases.json') as file:
        workdata = json.load(file)
        return workdata["workphrases"]