import os
import folium
import json
from datetime import datetime
import git
import shutil
import time
from hubspot_pz import HubspotPZ

TOKEN = os.getenv("HUBSPOT_AGENTS_MAP_TOKEN")
COLOR = [
    "#c0ccd7",  # 0 agenti – grigio azzurro chiaro
    "#a3bedb",  # 1 agente – azzurro chiaro
    "#66b1db",  # 2 agenti – azzurro medio
    "#00a7e1",  # 3 agenti – azzurro brillante
    "#006bb3",  # 4 agenti – blu intenso
    "#004987",  # 5 agenti – blu scuro
]


PROVINCE = {
    'AG': 'Agrigento', 'AL': 'Alessandria', 'AN': 'Ancona', 'AO': 'Aosta', 'AP': 'Ascoli Piceno', 'AQ': "L'Aquila", 'AR': 'Arezzo',
    'AT': 'Asti', 'AV': 'Avellino', 'BA': 'Bari', 'BG': 'Bergamo', 'BI': 'Biella', 'BL': 'Belluno', 'BN': 'Benevento',
    'BO': 'Bologna', 'BR': 'Brindisi', 'BS': 'Brescia',  'BT': 'Barletta-Andria-Trani', 'BZ': 'Bolzano', 'CA': 'Cagliari',
    'CB': 'Campobasso', 'CE': 'Caserta', 'CH': 'Chieti', 'CL': 'Caltanissetta', 'CN': 'Cuneo', 'CO': 'Como', 'CR': 'Cremona',
    'CS': 'Cosenza', 'CT': 'Catania', 'CZ': 'Catanzaro', 'EN': 'Enna', 'FC': 'Forlì-Cesena', 'FE': 'Ferrara', 'FG': 'Foggia',
    'FI': 'Firenze', 'FM': 'Fermo', 'FR': 'Frosinone', 'GE': 'Genova', 'GO': 'Gorizia', 'GR': 'Grosseto', 'IM': 'Imperia',
    'IS': 'Isernia', 'KR': 'Crotone', 'LC': 'Lecco', 'LE': 'Lecce', 'LI': 'Livorno', 'LO': 'Lodi', 'LT': 'Latina',
    'LU': 'Lucca', 'MB': 'Monza e della Brianza', 'MC': 'Macerata', 'ME': 'Messina', 'MI': 'Milano', 'MN': 'Mantova', 'MO': 'Modena', 
    'MS': 'Massa-Carrara', 'MT': 'Matera', 'NA': 'Napoli', 'NO': 'Novara', 'NU': 'Nuoro', 'OR': 'Oristano',
    'PA': 'Palermo', 'PC': 'Piacenza', 'PD': 'Padova', 'PE': 'Pescara', 'PG': 'Perugia', 'PI': 'Pisa',
    'PN': 'Pordenone', 'PO': 'Prato', 'PR': 'Parma', 'PT': 'Pistoia', 'PU': 'Pesaro e Urbino', 'PV': 'Pavia', 'PZ': 'Potenza', 'RA': 'Ravenna',
    'RC': 'Reggio di Calabria', 'RE': 'Reggio nell Emilia', 'RG': 'Ragusa', 'RI': 'Rieti', 'RM': 'Roma', 'RN': 'Rimini', 'RO': 'Rovigo',
    'SA': 'Salerno', 'SI': 'Siena', 'SO': 'Sondrio', 'SP': 'La Spezia', 'SR': 'Siracusa', 'SS': 'Sassari', 'SU': 'Sud Sardegna', 'SV': 'Savona',
    'TA': 'Taranto', 'TE': 'Teramo', 'TN': 'Trento', 'TO': 'Torino', 'TP': 'Trapani', 'TR': 'Terni', 'TS': 'Trieste', 'TV': 'Treviso',
    'UD': 'Udine', 'VA': 'Varese', 'VB': 'Verbano-Cusio-Ossola', 'VC': 'Vercelli', 'VE': 'Venezia', 'VI': 'Vicenza',
    'VR': 'Verona', 'VT': 'Viterbo', 'VV': 'Vibo Valentia'
}

geojsons = None

#######Funzioni di hubspot#################################################

def getProperty(propertyName, properties):
    return properties[propertyName]["value"] if propertyName in properties else ""

#######Funzioni di utility#################################################

def convertiData(timeMillisecond):
    if timeMillisecond == "":
        return None
    millisecond = int(timeMillisecond)
    timestamp = millisecond / 1000  # Converti millisecondi in secondi dividendo per 1000
    data = datetime.fromtimestamp(timestamp)
    return data.date()

def enumera_agenti_per_provincia(agenti):
    agentCounter = {}   #sigla -> numero agenti
    agentList = {}      #sigla -> elenco agenti
    
    for sigla in PROVINCE.keys():
        agentCounter[sigla] = 0
        agentList[sigla] = ""

    for agente in agenti:
        for sigla in [elemento.strip() for elemento in agente['province'].split(';') if elemento.strip()]:
            agentCounter[sigla] += 1
            agentList[sigla] += f"<br>(<strong>{agente['codice_mexal'] if agente['codice_mexal'] != None else ''}</strong>) {agente['nome_mexal']}"

    return agentCounter, agentList

def getColor(value):
    value = min(value, 5)
    return COLOR[value]

def readGeojson(sigla):
    global geojsons
    if geojsons == None:
        map_path = os.path.dirname(__file__)
        map_path = os.path.join(map_path, "italia.geojson")
        with open(map_path, 'r') as file:
            geojsons = json.load(file)

    for feature in geojsons["features"]:
        s = feature["properties"]["prov_acr"]
        if s == sigla:
            return feature
    print(sigla + " non trovata")
    return None

def readRegionGeojson():
    map_path = os.path.dirname(__file__)
    map_path = os.path.join(map_path, "regions.geojson")
    with open(map_path, 'r') as file:
        geojsons = json.load(file)
    return geojsons["features"]

#######Funzioni di mapping#################################################

def generateHTML(sigle, agentCounter, agentList, saving_path = None):
    if(saving_path == None):
        saving_path = os.path.join(os.path.dirname(__file__), 'agenti.html')

    if not os.path.exists(os.path.dirname(saving_path)):
        os.makedirs(os.path.dirname(saving_path))

    mappa_agenti = folium.Map(location=[42.5, 12.5], zoom_start=6)

    for sigla in sigle:
        style_function = lambda x, color=getColor(agentCounter[sigla]): {'fillColor': color, 'color': 'white', 'weight': 2, 'fillOpacity': 1}

        tooltipDictionary = {PROVINCE[sigla]: f"({sigla})",
               "Numero Agenti": agentCounter[sigla],
               "Elenco agenti": agentList[sigla]}
        testo = ""
        for key,value in tooltipDictionary.items():
            testo += f"<strong>{key}</strong> {value}<br>" if value != "" else ""
        
        folium.GeoJson(
            readGeojson(sigla),
            name=sigla,
            style_function=style_function,
            popup=folium.Popup(testo, min_width=100, max_width=400)
        ).add_to(mappa_agenti)

    for region in readRegionGeojson():
        folium.GeoJson(
            region,
            style_function=lambda x: {'fillColor': 'transparent', 'color': '#333333', 'weight': 5, 'fillOpacity': 0},
            tooltip=region['properties']['reg_name'],
            highlight_function=lambda x: {'weight': 5, 'color': '#000000'},
            interactive=False
        ).add_to(mappa_agenti)

    add_legend(mappa_agenti)

    mappa_agenti.save(saving_path)

    with open(saving_path, 'r+') as file:
        content = file.read()
        content = content.replace('<head>', f'<head><title>Mappa Agenti ({datetime.now().strftime("%d-%m-%Y %H:%M:%S")})</title>', 1)
        file.seek(0)
        file.write(content)
        file.truncate()
        
    return saving_path


def add_legend(mappa):
    legend_html = """
     <div style="
     position: fixed; 
     bottom: 50px; left: 50px; width: 160px; height: 180px; 
     background-color: white; 
     border:2px solid grey; 
     z-index:9999;
     font-size:14px;
     padding: 10px;
     ">
     <b>Numero Agenti</b><br>
     <i style="background:#c0ccd7;width:18px;height:18px;float:left;margin-right:5px;"></i> 0<br>
     <i style="background:#a3bedb;width:18px;height:18px;float:left;margin-right:5px;"></i> 1<br>
     <i style="background:#66b1db;width:18px;height:18px;float:left;margin-right:5px;"></i> 2<br>
     <i style="background:#00a7e1;width:18px;height:18px;float:left;margin-right:5px;"></i> 3<br>
     <i style="background:#006bb3;width:18px;height:18px;float:left;margin-right:5px;"></i> 4<br>
     <i style="background:#004987;width:18px;height:18px;float:left;margin-right:5px;"></i> 5+
     </div>
     """
    mappa.get_root().html.add_child(folium.Element(legend_html))

#######Applicazione#################################################

def updateMapRepository(agentCounter, agentList):
    working_dir = os.path.dirname(__file__)
    repo_url = "https://github.com/Nicolas-Personal-Zucchero/AgentMap"
    repo_url = "git@github.com:Nicolas-Personal-Zucchero/AgentMap.git"
    file_to_modify = "index.html"
    file_path = os.path.join(working_dir, file_to_modify)

#    print("Controllando la presenza della repository...")
#    if(not os.path.exists(repo_path)):
#        print("Repository non presente, clonando repository...")
#        git.Repo.clone_from(repo_url, repo_path)

    # Aggiungere, committare e pushare le modifiche
    print("Pullo la repository per possibili update")
    os.environ["GIT_SSH_COMMAND"] = "ssh -i /home/pz/.ssh/id_ed25519 -o IdentitiesOnly=yes"
    repo = git.Repo(working_dir)
    origin = repo.remote(name='origin')
    origin.pull()

    print("Genero la mappa agenti...")
    generateHTML(list(PROVINCE.keys()), agentCounter, agentList, saving_path=file_path)
    return
    print("Mappa agenti generata. Push in corso...")
    repo.index.add([file_path])
    repo.index.commit(f"Aggiornamento automatico della mappa degli agenti ({datetime.now().strftime('%d-%m-%Y %H:%M:%S')})")
    origin.push()

    print("Modifiche pushate con successo!")
    return

if __name__ == '__main__':
    h2 = HubspotPZ(TOKEN)

    agents_property_list = ["codice_mexal", "nome_mexal", "regione", "province", "data_fine_contratto", "escluso_da_assegnazione_clienti"]

    agents_ids = h2.getAgentsListMembersIds()
    agents = h2.getContactBatch(agents_ids, agents_property_list)
    agents = [a for a in agents if a["province"] is not None and a["data_fine_contratto"] is None and a["escluso_da_assegnazione_clienti"] == "false"]
    agents = sorted(agents, key=lambda x: int(x["id"]))

    agent_counter, agent_list = enumera_agenti_per_provincia(agents)
    
    updateMapRepository(agent_counter, agent_list)
