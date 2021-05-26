from dreaminsg_integrated_model.network_sim_models.transportation.network import *
net = Network("SiouxFalls_net.tntp", "SiouxFalls_trips.tntp")
net.userEquilibrium("FW", 400, 1e-4, net.averageExcessCost)

'''
"Anaheim_net.tntp, "Anaheim_trips.tntp"
"Austin_net.tntp","Austin_trips_am.tntp"
"Barcelona_net.tntp", "Barcelona_trips.tntp"
"berlin-center_net.tntp","berlin-center_trips.tntp"
"berlin-mitte-center_net.tntp","berlin-mitte-center_trips.tntp"
"berlin-mitte-prenzlauerberg-friedrichshain-center_net.tntp","berlin-mitte-prenzlauerberg-friedrichshain-center_trips.tntp"
"berlin-prenzlauerberg-center_net.tntp","berlin-prenzlauerberg-center_trips.tntp"
"berlin-tiergarten_net.tntp","berlin-tiergarten_trips.tntp"
"Birmingham_Net.tntp","Birmingham_Trips.tntp"
"ChicagoRegional_net.tntp","ChicagoRegional_trips.tntp"
"ChicagoSketch_net.tntp","ChicagoSketch_trips.tntp"
"EMA_net.tntp","EMA_trips.tntp"
"friedrichshain-center_net.tntp","friedrichshain-center_trips.tntp"
"Hessen-Asym_net.tntp", "Hessen-Asym_trips.tntp"
"Philadelphia_net.tntp","Philadelphia_trips.tntp"
"Terrassa-Asym_net.tntp","Terrassa-Asym_trips.tntp"
"Winnipeg_net.tntp","Winnipeg_trips.tntp"
"Winnipeg-Asym_net.tntp","Winnipeg-Asym_trips.tntp"
'''