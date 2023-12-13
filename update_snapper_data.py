import requests, os, json, time, random,csv
import datetime

curDir = os.path.dirname(os.path.realpath(__file__))

cardsPath = os.path.join(curDir, "data","cards.json")
tripsPath = os.path.join(curDir, "data","trips.json")
logsPath = os.path.join(curDir, "logs.csv")

def waitRandom():
    waitmlsec = random.randint(1,30)
    print(f"Waiting {datetime.timedelta(seconds=waitmlsec)}")
    time.sleep(waitmlsec)
    return None

def writeLog(message, status, card_number, now):
    with open(logsPath, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([message, status, card_number, now])

with open(cardsPath, "r") as f:
    cards = json.load(f)
    for i, card in enumerate(cards):
        waitRandom()
        now = str(datetime.datetime.now())
        card_num = card.get("card_number")
        payload = {"cvv":str(card.get("cvv"))}

        # get new data
        url = r"https://card-holder.snapper.co.nz/v1/cards/" + str(card_num) + "/transactions"
        print(url)
        res = requests.post(url, json=payload)
        print(res.status_code)
        if res.status_code == 200:
            newData = json.loads(res.text)

            # check if new data exists
            with open(tripsPath,"r") as f:
                currentData = json.load(f)
                for ele in newData:
                    ele["card_number"] = card_num
                    if ele not in currentData:
                        currentData.append(ele)

            # save updated data
            with open(tripsPath,"w") as f:
                f.write(json.dumps(currentData, indent=4))
            writeLog("POST request completed", "Success", card_num, now)

        else:
            writeLog("POST request failed", "Failure", card_num, now)
print("Completed")