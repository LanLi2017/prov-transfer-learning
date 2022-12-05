#!/usr/bin/env python
# coding: utf-8

# # Data Profiling with Python

# In[1]:


# @BEGIN python_remove_unnecessary_fields
# @IN input_menu @URI file:{project_root}/Menu.csv
# @IN input_menu_page @URI file:{project_root}/MenuPage.csv
# @IN input_menu_item @URI file:{project_root}/MenuItem.csv
# @IN input_dish @URI file:{project_root}/Dish.csv

# @OUT only_necessary_field_menu
# @OUT only_necessary_field_menu_page
# @OUT only_necessary_field_menu_item
# @OUT only_necessary_field_dish

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# # Check null columns

# In[2]:


# @BEGIN check_null_columns
# @IN input_menu
# @IN input_menu_page
# @IN input_menu_item
# @IN input_dish

def check_null_columns(file_name):
    df = pd.read_csv(file_name)
#     columns_with_all_null = df.columns[df.isnull().all()]
    print('###############################')
    print('{}'.format(file_name))
#     print('Drop columns where all values are NA {}'.format(columns_with_all_null.values))
#     df.drop(columns_with_all_null, axis='columns', inplace=True)

    ### Identify columns with too many missing values
    for col in df.columns:
        count_nan = df[col].isnull().sum()
        percentage_missing = count_nan / df.size
        print('{:30s}\t{}\t{:.2f}%\t({:.10f}%)'.format(col, count_nan, percentage_missing*100, percentage_missing*100))
    return df

menu = check_null_columns('Menu.csv')
menu_page = check_null_columns('MenuPage.csv')
menu_item = check_null_columns('MenuItem.csv')
dish = check_null_columns('Dish.csv')

# @END check_null_columns


# # Remove un-necessary columns
# We will remove un-ncessary columns so that we can do our operations more efficiently. One caveate is that dish_id has 0.00% null values, but actually it has null values (0.0020061582%). This rows may violate constraints or really do not have dish items. We are not sure about this, so we will remove these rows.

# In[3]:


# @BEGIN remove_unnecessary_fields
# @IN input_menu
# @IN input_menu_page
# @IN input_menu_item
# @IN input_dish

menu = menu.drop(['keywords', 'language', 'location_type', 'name', 'sponsor', 'event', 'venue',
                  'physical_description', 'occasion', 'notes', 'call_number', 'page_count', 'dish_count'], axis='columns')
menu_page = menu_page.drop(['page_number', 'image_id', 'full_height', 'full_width', 'uuid'], axis='columns')
menu_item = menu_item.drop(['high_price', 'created_at', 'updated_at', 'xpos', 'ypos'], axis='columns')
dish = dish.drop(['description', 'menus_appeared', 'times_appeared', 'first_appeared', 'last_appeared', 'lowest_price', 'highest_price'], axis='columns')

before = menu_item.shape[0]
menu_item.dropna(subset=['dish_id'], inplace=True)
after = menu_item.shape[0]
print('MenuItem na value delete: {}'.format(before-after))
menu_item["dish_id"] = menu_item["dish_id"].astype(np.int64)

menu.to_csv('./NYPL_only_necessary_columns/Menu.csv', index=False)
menu_page.to_csv('./NYPL_only_necessary_columns/MenuPage.csv', index=False)
menu_item.to_csv('./NYPL_only_necessary_columns/MenuItem.csv', index=False)
dish.to_csv('./NYPL_only_necessary_columns/Dish.csv', index=False)

# @OUT only_necessary_field_menu
# @OUT only_necessary_field_menu_page
# @OUT only_necessary_field_menu_item
# @OUT only_necessary_field_dish

# @END remove_unnecessary_fields


# In[4]:


get_ipython().system('rm -f NYPL_only_necessary_columns.zip')
get_ipython().system('zip NYPL_only_necessary_columns.zip ./NYPL_only_necessary_columns/*.csv')


# # Make After_OpenRefine.zip in OpenRefine
# Now we are ready to do OpenRefine operations with NYPL_only_necessary_columns.zip. Once OpenRefine job finished, export refined data to After_OpenRefine.zip file again in order to do more operations in Python.

# # Cicken detection

# In[10]:


# chicken finding test
# Chicken: Chick, (In Franch) Poulette,  Coquille, Poulet, Poussin, Poularde, Coq, Geline, Supreme, Aileron, Cuisse
poulet = dish.name.str.contains('poulet')
dish.name[poulet]


# In[11]:


# List of chicken dishes: https://en.wikipedia.org/wiki/List_of_chicken_dishes
chicken_dishes = pd.read_csv("chicken_dishes.txt")
chicken_idx = chicken_dishes["name"].str.lower().str.contains("chicken")
chicken_variants = chicken_dishes[~chicken_idx]
chicken_var_words = chicken_variants.name.str.lower().str.split(expand=True).stack().value_counts()
chicken_words = chicken_var_words[chicken_var_words > 1]
chicken_words = chicken_words.drop(['à', 'au', 'wing',
                                    'shish',    # skewer (a long piece of wood or metal used for holding pieces of food)
                                    'biryani',  # Indian fried rice
                                    'adobo',    # Philippines's cooking technique, not a dish name
                                    'nasi',     # Indonesian rice
                                    'kai',      # Thailand soup
                                    ], axis=0)  # delete the rows with some labels
print(chicken_words)
chicken_words = chicken_words.append(pd.Series({'chicken': 100, 'coq':1, 'poulet':1, 'poussin': 1, 'poulette': 1, 'karaage': 1, 'yassa': 1}))
chicken_words = chicken_words.sort_values(ascending=False)
#print(chicken_words)
# print(chicken_words.index.values)


# In[12]:


# https://stackoverflow.com/questions/53350793/how-to-check-if-pandas-column-has-value-from-list-of-string
chicken_checks = dish.name.apply(lambda x: any([k in x for k in chicken_words.index.values]))
chicken_rows = dish.name[chicken_checks == True]
chicken_rows.describe()


# In[13]:


chicken_rows.head()


# In[14]:


dish_after_openrefine = pd.read_csv('./After_OpenRefine/Dish.csv')

dish_after_openrefine["is_chicken"] = chicken_checks
dish_after_openrefine["is_chicken"] = dish_after_openrefine["is_chicken"].replace({True: 'Y', False: 'N'})

dish_after_openrefine.to_csv('./afterAddingCurrAndNyc/Dish.csv', index=False)


# # NYC detection

# In[15]:


# load from After_OpenRefine.zip
menu_after_openrefine = pd.read_csv('./After_OpenRefine/Menu.csv')


# In[16]:


menu_after_openrefine["is_in_nyc"] = menu_after_openrefine['place'].str.lower().str.contains(r'\b(ny|nyc|new york)\b',regex=True) | menu_after_openrefine['location'].str.lower().str.contains(r'\b(ny|nyc|new york)\b',regex=True)
menu_after_openrefine["is_in_nyc"] = menu_after_openrefine["is_in_nyc"].replace({True: 'Y', False: 'N'})
menu_after_openrefine["is_in_nyc"].head(n=20)


# # Convert currency rates

# In[17]:


#print(menu_after_openrefine.currency.value_counts())

currency_map = {
    'dollars': 1,
    'deutsche marks': 0.63,
    'francs': 0.18,
    'canadian dollars':0.793,
    'swiss francs':1.087,
    'shillings':0.085,
    'swedish kronor (sek/kr)':0.115,
    'italian lire':0.0006,
    'cents':0.01,
    'uk pounds':1.377,
    'belgian francs':0.029,
    'mexican pesos':0.05,
    'dutch guilders':0.535,
    'austrian schillings':0.085,
    'danish kroner':0.158,
    'yen':0.009,
    'pesetas':0.007,
    'euros':1.181,
    'escudos':0.005,
    'austro-hungarian kronen':0.021,
    'hungarian forint':0.003,
    'drachmas':0.003,
    'israeli lirot (1948-1980)':0.304,
    'norwegian kroner':0.114,
    'icelandic krónur':0.008,
    'quetzales':0.129,
    'argentine peso':0.01,
    'finnish markka':0.198,
    'lats':1.68,
    'sol':0.25,
    'cuban pesos':0.041,
    'złoty':0.257,
    'brazilian cruzeiros':0.00007131,
    'uruguayan pesos':0.022,
    'qatari riyal':0.274,
    'australian dollars':0.74,
    'new taiwan dollar':0.036,
    'bermudian dollars':1,
    'moroccan dirham':0.111,
    'monégasque francs':0.18,
    'pence':0.01387,
    'straits dollar (1904-1939)':0.256,
    np.nan: 1
}

menu_after_openrefine["to_dollar_rate"] = menu_after_openrefine.currency.apply(lambda x: currency_map[x])
menu_after_openrefine.to_csv('./afterAddingCurrAndNyc/Menu.csv', index=False)


# In[18]:


# @END CS513-Team15-FinalProject


# In[ ]:




