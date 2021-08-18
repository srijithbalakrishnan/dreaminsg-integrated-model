import ogr,os
myDir = 'C:/Users/srijith/Dropbox/Intra-CREATE Seed Grant/Integrated Model/dreaminsg_integrated_model/infrarisk/data/networks/micropolis/gis/'

if os.path.exists (myDir) == False:
   print("Path does not exist")
else:
    for vLayer in iface.mapCanvas().layers():
        if vLayer.type()==0: #Save only shapefiles in the Layer Panel 
            QgsVectorFileWriter.writeAsVectorFormat(vLayer, myDir + vLayer.name() + ".shp", "utf-8", vLayer.crs(),  "ESRI Shapefile")
            print(vLayer.name() + " saved successfully")