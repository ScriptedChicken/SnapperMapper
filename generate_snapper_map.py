import requests, json, os

TEST = False

def returnBalance(json_obj):
    return json_obj[0].get("balanceAfterCents") / 100

def returnSqlList(x):
    if isinstance(x, list) == False:
        x = list(x)
    return str(x).replace("[","(").replace("]",")")

def setVisibility(lyrID, visible=True):
    QgsProject.instance().layerTreeRoot().findLayer(lyrID).setItemVisibilityChecked(visible)

def cleanup():
    for lyr in QgsProject.instance().mapLayers().values():
        if lyr.name() in ["Frequency of Stop Usage", "Extracted Trip Data", "Ordenado"]:
            QgsProject.instance().removeMapLayer(lyr)
        else:
            lyr.setSubsetString(None)

def removeDuplicateLabels(lyr):
    uniqueLabels = []
    with edit(lyr):
        for ftr in lyr.getFeatures():
            stopName = ftr["stopName"]
            if stopName in uniqueLabels:
                ftr["stopName"] = ""
                lyr.updateFeature(ftr)
            else:
                uniqueLabels.append(stopName)

def setStylePath(layer, qlm):
    stylePath = os.path.join(QgsProject.instance().homePath(),'styles',qlm)
    layer = QgsProject.instance().mapLayersByName(layer.name())[0]
    res = layer.loadNamedStyle(stylePath)
    layer.triggerRepaint()
    return layer

def getUniqueValues(lyr, fld, onlySelected=False):
    idx = lyr.fields().indexOf(fld)
    result = lyr.uniqueValues(idx)
    if onlySelected:
        result = []
        for ftr in lyr.getSelectedFeatures():
            result.append(ftr[idx])
    else:
        result = lyr.uniqueValues(idx)
    return result

homePath = QgsProject.instance().homePath()   

# get stored card numbers
cardsPath = os.path.join(homePath, "data","cards.json")
with open(cardsPath, "r") as f:
    cards = json.load(f)
    for card in cards:
        card_num = card.get("card_number")

        # reset project layers
        cleanup()

        # load saved trips JSON
        tripsPath = os.path.join(homePath, "data","trips.json")
        trips = json.loads(open(tripsPath).read())

        ### Convert Trips to GeoJSON Stops ###
        ptStops = QgsProject.instance().mapLayersByName("PT Stops")[0]
        geoJSON = {
            "type": "FeatureCollection",
            "features": None
        }
        features = []
        for properties in trips:
            # only populate with details of current card number
            isValid = properties.get("card_number") == card_num and properties.get("transactionType") == "TransportTransaction"
            if isValid:
                # get coords from corresponding bus stop
                stopName = properties.get("stopName")
                ptStops.selectByExpression(f'"Service" = \'{stopName}\'',QgsVectorLayer.SetSelection)
                for ftr in ptStops.getSelectedFeatures():
                    geom = ftr.geometry()
                    coordinates = [geom.asPoint().x(), geom.asPoint().y()]
                ftr = {
                "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": coordinates
                    },
                        "properties": properties
                }
                features.append(ftr)
        geoJSON['features'] = features

        # save geojson
        homePath = QgsProject.instance().homePath()
        fullPath = os.path.join(homePath,"data","trips.geojson")
        with open(fullPath, 'w') as f:
            f.write(json.dumps(geoJSON, indent=4))

        # load geoJSON as layer
        extractedTripData = QgsVectorLayer(fullPath,"Extracted Trip Data","ogr")
        extractedTripData.setCrs(QgsProject.instance().crs())
        QgsProject.instance().addMapLayer(extractedTripData)

        setStylePath(extractedTripData, 'extractedTripData.qml')

        ### Display Stop Usage ###
        res = processing.run("native:dissolve", {
            'INPUT': extractedTripData,\
            'FIELD': "stopName",\
            'SEPARATE_DISJOINT': False,\
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        frequencyStopUseage = res["OUTPUT"]
        dp = frequencyStopUseage.dataProvider()
        dp.addAttributes([QgsField("numberOfUses", QVariant.Int)])
        frequencyStopUseage.updateFields()
        frequencyStopUseage.setName("Frequency of Stop Usage")
        QgsProject.instance().addMapLayer(frequencyStopUseage)

        # set style
        setStylePath(frequencyStopUseage, 'frequencyOfStopUsage.qml')

        # populate numberOfUses values with underlying selected trip points
        idx = frequencyStopUseage.fields().indexOf('stopName')
        usedStopNames = frequencyStopUseage.uniqueValues(idx)

        usesDict = {}
        for stopName in usedStopNames:
            expression = f'"stopName" = \'{stopName}\'' 
            frequencyStopUseage.setSubsetString(expression)
            processing.run("native:selectbylocation", {
                'INPUT': extractedTripData,\
                'PREDICATE': [0],\
                'INTERSECT': frequencyStopUseage,\
                'METHOD': 0,\
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })
            
            count = extractedTripData.selectedFeatureCount()
            # print(f"{expression}: {count}")
            for ftr in frequencyStopUseage.getFeatures():
                with edit(frequencyStopUseage):
                    ftr['numberOfUses'] = count
                    frequencyStopUseage.updateFeature(ftr)
        frequencyStopUseage.setSubsetString(None)

        ### Filter Used Routes ###
        publicTransportRoutes = QgsProject.instance().mapLayersByName("Public Transport Routes")[0]
        usedRouteNumbers = getUniqueValues(frequencyStopUseage, 'routeNumber')
        sqlList = returnSqlList(usedRouteNumbers)
        expression = f'"SERVICE" IN {sqlList}'
        publicTransportRoutes.setSubsetString(expression)

        ### Highlight frequented suburbs ###
        nzSuburbs = QgsProject.instance().mapLayersByName("NZ Suburbs Mask")[0]
        nzSuburbsLabels = QgsProject.instance().mapLayersByName("NZ Suburbs")[0]
        processing.run("native:selectbylocation", {
            'INPUT': nzSuburbs,\
            'PREDICATE': [0],\
            'INTERSECT': frequencyStopUseage,\
            'METHOD': 0,\
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        suburbIDs = getUniqueValues(nzSuburbs, 'id', onlySelected=True)
        sqlList = returnSqlList(suburbIDs)
        expression = f'"id" NOT IN {sqlList}'
        nzSuburbs.setSubsetString(expression)
        expression = f'"id" IN {sqlList}'
        nzSuburbsLabels.setSubsetString(expression)
        
        # remove un-needed labels
        # removeDuplicateLabels(extractedTripData)

        ### Zoom to Frequency Points ###
        canvas = iface.mapCanvas()
        freqLyr = QgsProject.instance().mapLayersByName(frequencyStopUseage.name())[0]
        extent = freqLyr.extent()
        canvas.setExtent(extent)
        canvas.zoomByFactor(0.6)
        canvas.refresh()

        # make sure that frequency stop useage layer not showing
        setVisibility(frequencyStopUseage.id(), False)

        ### Fill Print Layout and Export ###
        manager = QgsProject.instance().layoutManager()
        homePath = QgsProject.instance().homePath()
        layout = manager.layoutByName("visualise_snapper_info")

        # get current balance
        currentBalance = 0
        idx = extractedTripData.fields().indexOf('transactionDateTime')
        mostRecentTime = extractedTripData.maximumValue(idx)
        dtStr = f'{mostRecentTime.toPyDateTime():%d/%m/%Y %H:%M:%S}'
        expression = f'"transactionDateTime" = to_datetime(\'{dtStr}\', \'d/M/yyyy hh:mm:ss\')'
        extractedTripData.selectByExpression(expression)
        for ftr in extractedTripData.getSelectedFeatures():
            currentBalance = ftr['balanceAfterCents']
        currentBalanceFormatted = round(float(currentBalance/100),2)
        extractedTripData.removeSelection()

        # update details
        details = layout.itemById('Details')
        detailsText = f"Card Number: {card_num}\nCurrent Balance: ${currentBalanceFormatted}"
        details.setText(detailsText)

        # update plots
        res = processing.run("native:orderbyexpression", {
            'INPUT': freqLyr,\
            'EXPRESSION': "\"transactionDateTime\"",\
            'ASCENDING': True,\
            'NULLS_FIRST': False,\
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        plotData = res["OUTPUT"]
        QgsProject.instance().addMapLayer(plotData)
        setVisibility(plotData.id(), visible=False)
        plot = layout.itemById('Plot_Balance')
        settings = plot.plot_settings[0]
        settings.source_layer_id = plotData.id()
        plot.refresh()

        plot = layout.itemById('Plot_Time_By_Location')
        settings = plot.plot_settings[0]
        settings.source_layer_id = extractedTripData.id()
        plot.refresh()

        # update map in layout
        map = layout.itemById('Mapa 1')
        map.zoomToExtent(canvas.extent())
        exporter = QgsLayoutExporter(layout)
        exportPath = os.path.join(homePath, 'maps', f'{card_num}.png')
        exporter.exportToImage(exportPath, QgsLayoutExporter.ImageExportSettings())
        
        print(f"Exported {exportPath}")

print("Complete")