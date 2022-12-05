# @BEGIN overall_workflow
# @IN input_menu @URI file:{project_root}/Menu.csv
# @IN input_menu_page @URI file:{project_root}/MenuPage.csv
# @IN input_menu_item @URI file:{project_root}/MenuItem.csv
# @IN input_dish @URI file:{project_root}/Dish.csv
# @IN exchange_rate @URI file:{project_root}/currency_convert_plan.xlsx
# @IN chicken_dish_list @URI file:{project_root}/chicken_dishes.txt

# @OUT analysis_result

# --------------------------------------------------
# @BEGIN python_remove_unnecessary_fields

# @IN input_menu
# @IN input_menu_page
# @IN input_menu_item
# @IN input_dish

# @OUT only_necessary_field_menu @URI file:{project_root}/NYPL_only_necessary_columns/Menu.csv
# @OUT only_necessary_field_menu_page @URI file:{project_root}/NYPL_only_necessary_columns/MenuPage.csv
# @OUT only_necessary_field_menu_item @URI file:{project_root}/NYPL_only_necessary_columns/MenuItem.csv
# @OUT only_necessary_field_dish @URI file:{project_root}/NYPL_only_necessary_columns/Dish.csv

# @END python_remove_unnecessary_fields

# ---------------------------------------------------
# @BEGIN openrefine_clean

# @IN only_necessary_field_menu
# @IN only_necessary_field_menu_page
# @IN only_necessary_field_menu_item
# @IN only_necessary_field_dish

# @OUT cleaned_menu @URI file:{project_root}/After_OpenRefine/Menu.csv
# @OUT cleaned_menu_page @URI file:{project_root}/After_OpenRefine/MenuPage.csv
# @OUT cleaned_menu_item @URI file:{project_root}/After_OpenRefine/MenuItem.csv
# @OUT cleaned_dish @URI file:{project_root}/After_OpenRefine/Dish.csv
# @OUT currency_types @URI file:{project_root}/currency_types.txt

# @END openrefine_clean

# ---------------------------------------------------
# @BEGIN map_currency_exchange

# @IN currency_types
# @IN exchange_rate

# @OUT currency_exchange_rate

# @END map_currency_exchange

# ---------------------------------------------------
# @BEGIN python_add_currency_nyc_chicken

# @IN cleaned_menu
# @IN cleaned_dish
# @IN chicken_dish_list
# @IN currency_exchange_rate

# @OUT added_isnyc_currency_fields_menu @URI file:{project_root}/afterAddingCurrAndNyc/Menu.csv
# @OUT added_ischicken_field_dish @URI file:{project_root}/afterAddingCurrAndNyc/Dish.csv

# @END python_add_currency_nyc_chicken

# ---------------------------------------------------
# @BEGIN mysql_ic_check

# @IN added_isnyc_currency_fields_menu
# @IN added_ischicken_field_dish
# @IN cleaned_menu_page
# @IN cleaned_menu_item

# @OUT result_menu
# @OUT result_menu_page
# @OUT result_menu_item
# @OUT result_dish

# @END mysql_ic_check

# ---------------------------------------------------
# @BEGIN mysql_query_analyze

# @IN result_menu
# @IN result_menu_page
# @IN result_menu_item
# @IN result_dish

# @OUT analysis_result

# @END mysql_query_analyze

# ---------------------------------------------------
# @END overall_workflow
