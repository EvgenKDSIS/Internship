import requests
import os
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
from tqdm import tqdm

class vac_parser:
    
    def __init__(self, 
                 url: str, 
                 path: str, 
                 text: str,
                 search_field=None, 
                 dates=None):
        
        self.url = url
        self.path = path
        
        self.data = pd.DataFrame({
            'id':[],
            'name':[],
            'company':[],
            'industries':[],
            'city':[],
            'experience':[],
            'salary':[],
            'responses':[],
            'description':[],
            'key_skills':[],
            'url':[]
        })
        
        self.text = text
        
        self.par = {}
        if search_field != None:
            self.par['vacancy_search_fields'] = search_field
        if dates != None:
            self.par['date_from'] = dates[0]
            self.par['date_to'] = dates[1]
        self.par['text'] = self.text 
        self.par['area'] = '113'
        self.par['per_page'] = '10'
        self.par['page'] = 1
        self.par['responses_count_enabled'] = True
        
        
        self.vacancies_info = requests.get(self.url, params=self.par, verify=False).json()
        self.vacancies_count = self.vacancies_info['found']
        self.num_pages = self.vacancies_info['pages']
        
        if (self.num_pages >= 200) and ((self.vacancies_count/10) > 200):
            print(f'Вакансий слишком много для парсинга - {self.vacancies_count}, делим по дням')
        else:
            print(f'Количество вакансий для парсинга - {self.vacancies_count}')
            print('Количество страниц для парсинга:', self.num_pages)
            
#     def make_list_for_parsing(self, par):
        
#         dates_list = []
#         days_max = 30
#         start_date = datetime.today()
#         last_date = datetime.today() - timedelta(days=days_max)
       
#         self.par['date_from'] = str(last_date.date())
#         self.par['date_to'] = str(start_date.date())
        
#         vacancies_info = requests.get(self.url, params=self.par, verify=False).json()
#         vacancies_count = self.vacancies_info['found']
#         num_pages = self.vacancies_info['pages']
        
#         if (num_pages >= 200) and ((vacancies_count/10) > 200):
#             days_max //= 2
#             last_date = datetime.today() - timedelta(days=days_max)
#             self.par['date_from'] = str(last_date.date())
#             vacancies_info = requests.get(self.url, params=self.par, verify=False).json()
#             vacancies_count = self.vacancies_info['found']
#             num_pages = self.vacancies_info['pages']
        
    
    def check_num_pages(self):
        print('Количество страниц для парсинга:', self.num_pages)

    def vacancie_parser(self, j: dict):

        vacancie_info = {}

        vacancie_info['id'] = j['id']
        vacancie_info['name'] = j['name']
        vacancie_info['company'] = j['employer']['name']
        vacancie_info['city'] = j['area']['name']
        vacancie_info['experience'] = j['experience']['name']

        if j['salary'] is not None:

            salary = str()
            if ((j['salary']['from'] is not None) and (j['salary']['to']) is not None):
                salary = 'от ' + str(j['salary']['from'])
                salary += ' до ' + str(j['salary']['to'])
                salary += ' ' + str(j['salary']['currency'])

            elif ((j['salary']['from'] is not None) and (j['salary']['to']) is None):
                salary = 'от ' + str(j['salary']['from'])
                salary += ' ' + str(j['salary']['currency'])

            else:
                salary += 'до ' + str(j['salary']['to'])
                salary += ' ' + str(j['salary']['currency'])

            if j['salary']['gross'] is True:
                salary += ' до вычета'
            elif j['salary']['gross'] is False: 
                salary += ' на руки'
            else:
                pass

            vacancie_info['salary'] = salary
        else:
            vacancie_info['salary'] = j['salary']

        vacancie_info['description'] = j['description']

        s = []
        for i in j['key_skills']:
            s.append(i['name'])
        vacancie_info['key_skills'] = ', '.join(s)

        return vacancie_info
    
    def get_info_from_page(self, page: dict):

        for i, vacancie in enumerate(page['items']):

            vac_url = vacancie['url']
            try:
                emp_url = vacancie['employer']['url']
            except:
                print(vac_url)
                break
                
            vac_info = requests.get(vac_url, verify=False, timeout=10).json()
            
            time.sleep(.2)
            emp_info = requests.get(emp_url, verify=False, timeout=10).json()

            vacancie_info = self.vacancie_parser(vac_info)
            try: 
                vacancie_info['industries'] = emp_info['industries'][0]['name']
            except:
                vacancie_info['industries'] = None
            vacancie_info['responses'] = vacancie['counters']['responses']
            vacancie_info['url'] = vacancie['alternate_url']

            self.data.loc[len(self.data)] = vacancie_info

        time.sleep(.2)
        
    def start_final_parse(self):
        
        for page_number in tqdm(range(0, self.num_pages)):

            parameters = {
                'text': self.text, 
                'area':'113',
                'per_page':'10', 
                'page': page_number, 
                'responses_count_enabled': True
            }

            hh_page = requests.get(self.url, params=parameters, verify=False, timeout=10).json()
            try:
                self.get_info_from_page(hh_page)
            except Exception as e:
                print(e)
                self.last_page = page_number
                self.save_checkpoint(page_number)
                break
            
    def save_checkpoint(self, page):
        text = self.text.replace(' ', '_').replace('"', '_')
        self.data.to_csv(self.path + '/checkpoints/' + f'page_{page}_' + text + '.csv')
        
    def load_from_checkpoint(self, last_page):
        
        for page_number in tqdm(range(last_page, self.num_pages)):
            
            parameters = {
                'text': self.text, 
                'area':'113',
                'per_page':'10', 
                'page': page_number, 
                'responses_count_enabled': True
            }

            hh_page = requests.get(self.url, params=parameters, verify=False, timeout=10).json()
            try:
                self.get_info_from_page(hh_page)
            except Exception as e:
                print(e)
                self.last_page = page_number
                self.save_checkpoint(page_number)
                break
        
    def save_file(self, name: str):
        self.data.to_csv(self.path + '/' + name + '.csv')