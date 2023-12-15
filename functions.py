import streamlit as st
import sqlalchemy as db
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import openai

#Placer votre clé API dans la variable ci-dessous
openai.api_key = "API_Keys"

# Requête HTTP
url = 'https://www.leagueoflegends.com/fr-fr/champions/'
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

champions = soup.find('div', class_='style__List-sc-13btjky-2').find_all('a')
img = 'https://images.contentstack.io/v3/assets/blt731acb42bb3d1659/blt570145160dd39dca/5db05fa8347d1c6baa57be25/RiotX_ChampionList_aatrox.jpg?quality=90&width=250'



# Show sidebar
def show_sidebar():
    # Sidebar
    st.sidebar.title("Kevin Duranty")
    st.sidebar.image("https://www.leagueoflegends.com/static/logo-1200-04b3cefafba917c9c571f9244fd28a1e.png")
    st.sidebar.subheader("Description de l'application")
    st.sidebar.markdown("Cette application permet de collecter des données du site League of Legends et de discuter avec un bot expert du jeu.")
    st.sidebar.link_button("Lien vers le site", "https://www.leagueoflegends.com/fr-fr/")


def get_champion_info(champion, url):
            name = champion.find('span', 'style__Name-sc-n3ovyt-2').text
            img = champion.find('img').get('src')
            
            champion_link = url + champion.get('href').split('/')[-2]
            
            response_champion = requests.get(champion_link)
            soup_champion = BeautifulSoup(response_champion.text, "html.parser")
            desciption = soup_champion.find('div', 'style__Desc-sc-8gkpub-9 jheTpK').text
            role = soup_champion.find('div', 'style__SpecsItemValue-sc-8gkpub-15').text

            return name, img, desciption, role, champion_link

# Convert DataFrame to csv
@st.cache_resource
def convert_df(df):
    return df.to_csv().encode('utf-8')


# Gestion d'une base de données

class DataBase():
    def __init__(self, name_database='database'):
        self.name = name_database
        self.url = f"sqlite:///{name_database}.db"
        self.engine = db.create_engine(self.url)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.table = self.engine.table_names()


    def create_table(self, name_table, **kwargs):
        colums = [db.Column(k, v, primary_key = True) if 'id_' in k else db.Column(k, v) for k,v in kwargs.items()]
        db.Table(name_table, self.metadata, *colums)
        self.metadata.create_all(self.engine)
        print(f"Table : '{name_table}' are created succesfully")

    def read_table(self, name_table, return_keys=False):
        table = db.Table(name_table, self.metadata, autoload=True, autoload_with=self.engine)
        if return_keys:table.columns.keys()
        else : return table


    def add_row(self, name_table, **kwarrgs):
        name_table = self.read_table(name_table)

        stmt = (
            db.insert(name_table).
            values(kwarrgs)
        )
        self.connection.execute(stmt)
        print(f'Row id added')

    def select_table(self, name_table):
        name_table = self.read_table(name_table)
        stm = db.select([name_table])
        return self.connection.execute(stm).fetchall()

def show_champions(champion, url, nb_champion):
        
        # Configurations de la base de données
        database = DataBase('database_lol')
        try:database.create_table('champions', 
                                  id_champion=db.String(50), 
                                  img=db.String(50), 
                                  desciption=db.String(50), 
                                  role=db.String(50), 
                                  champion_link=db.String(50),
                                  time=db.String(50))
        except:pass

        data_champion = {}
        for champion in champions[:nb_champion]:
            col1, col2 = st.columns(2)
            
            # Get champion info
            name, img, desciption, role, champion_link = get_champion_info(champion, url)

            try:     
                with col1:
                    st.subheader(name)                                                      # Names
                    st.write('Rôle : '+role)                                                # Roles
                    st.write(desciption)                                                    # Descriptions
                    st.link_button(name,champion_link)                                      # Links       
                with col2:st.image(img)                                                     # Images

                data_champion[name] = {
                    'role': role,
                    'desciption': desciption,
                    'champion_link': champion_link,
                    'img': img
                }
                try:
                    database.add_row('champions', 
                                     id_champion=name, 
                                     img=img, 
                                     desciption=desciption, 
                                     role=role, 
                                     champion_link=champion_link,
                                     time=datetime.now().strftime("%d/%m/%Y %H:%M"))
                except:pass
    
            except:pass
        
        df = pd.DataFrame(data_champion).T

        csv = convert_df(df)

        st.sidebar.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='large_df.csv',
            mime='text/csv',
        )

def chat_openAI(question, database):
    data_lol = str(database.select_table('champions'))[:2000]
    reponse = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
            "content": f"Tu es un expert du jeu Leag of Legend, voici les donées dont tu disposes '{data_lol}'. Tu réponds aux utilisateurs de manière courtoise et tu ne fais pas de fautes d'orthographe."},
            {"role": "user",
            "content": "Voici la question/remarque de l'utilisateur :" + question},
        ],
        max_tokens=1000,
        temperature=0.9,
    )

    return reponse['choices'][0]['message']["content"]