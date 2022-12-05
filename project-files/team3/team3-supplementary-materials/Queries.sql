--------------------SQLite Data Cleaning Queries------------------------------

--Query to create the CLEANED MenuAggClean table to store the joint dataset 
SELECT 
    m.location
    , m.place
    , m.sponsor
    , agg.dish_name
    , agg.dish_lowest_price
    , agg.dish_highest_price
    , agg.mi_price
    , agg.mi_high_price
FROM MenuClean m
JOIN (
        SELECT 
            mp.id AS mp_id
            , mp.menu_id
            , md.mi_id
            , md.mi_dish_id
            , md.mi_price
            , md.mi_high_price
            , md.dish_name
            , md.dish_lowest_price
            , md.dish_highest_price
        FROM MenuPage mp
        JOIN (
                SELECT 
                    mi.menu_page_id
                    , mi.id AS mi_id
                    , mi.dish_id AS mi_dish_id
                    , mi.price AS mi_price
                    , mi.high_price AS mi_high_price
                    , d.name AS dish_name
                    , d.lowest_price AS dish_lowest_price
                    , d.highest_price AS dish_highest_price 
                FROM MenuItem mi
                JOIN DishClean d
                ON mi.dish_id = d.id
            ) md
        ON mp.id = md.menu_page_id
    ) agg
ON m.id = agg.menu_id
WHERE
    agg.mi_price > 0
    AND m.location IS NOT NULL
    AND m.location != 'Unknown'
    AND m.if_NY = 'true';


--Query to create the RAW MenuAggRaw table to store the joint dataset 
SELECT 
    m.location
    , m.place
    , m.sponsor
    , agg.dish_name
    , agg.dish_lowest_price
    , agg.dish_highest_price
    , agg.mi_price
    , agg.mi_high_price
FROM MenuRaw m
JOIN (
        SELECT 
            mp.id AS mp_id
            , mp.menu_id
            , md.mi_id
            , md.mi_dish_id
            , md.mi_price
            , md.mi_high_price
            , md.dish_name
            , md.dish_lowest_price
            , md.dish_highest_price
        FROM MenuPage mp
        JOIN (
                SELECT 
                    mi.menu_page_id
                    , mi.id AS mi_id
                    , mi.dish_id AS mi_dish_id
                    , mi.price AS mi_price
                    , mi.high_price AS mi_high_price
                    , d.name AS dish_name
                    , d.lowest_price AS dish_lowest_price
                    , d.highest_price AS dish_highest_price 
                FROM MenuItem mi
                JOIN DishRaw d
                ON mi.dish_id = d.id
            ) md
        ON mp.id = md.menu_page_id
    ) agg
ON m.id = agg.menu_id
WHERE
    agg.mi_price > 0
    AND m.location IS NOT NULL;


--Query against the joint dataset MenuAggClean table to fulfill target use case
--Target Use Case: “In the state of NY, what is the average price of each dish, 
--                  and how many distinct locations offer each dish?”
SELECT 
    dish_name
    , COUNT(DISTINCT location)
    , AVG(mi_price)
FROM MenuAggClean
GROUP BY dish_name;


-------------------------SQLite ICV Check Queries-----------------------------------

--ICV_1: Confirm removal of unnecessary ‘[]’, ‘{}’, ‘“”’, 
--       '()', ( )', or ‘?’ in location column
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    location LIKE '%[]%'
    OR location LIKE '%{}%'
    OR location LIKE '%""%'
    OR location LIKE '%?%'
    OR location LIKE '%()%'
    OR location LIKE '%( )%';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    location LIKE '%[]%'
    OR location LIKE '%{}%'
    OR location LIKE '%""%'
    OR location LIKE '%?%'
    OR location LIKE '%()%'
    OR location LIKE '%( )%';


--ICV_2: Confirm removal of unnecessary ‘[]’, ‘{}’, ‘“”’, 
--       '()', '( )', or ‘?’ characters in dish_name column
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    dish_name LIKE '%[]%'
    OR dish_name LIKE '%{}%'
    OR dish_name LIKE '%""%'
    OR dish_name LIKE '%?%'
    OR dish_name LIKE '%()%'
    OR dish_name LIKE '%( )%';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    dish_name LIKE '%[]%'
    OR dish_name LIKE '%{}%'
    OR dish_name LIKE '%""%'
    OR dish_name LIKE '%?%'
    OR dish_name LIKE '%()%'
    OR dish_name LIKE '%( )%';


--ICV_3: Confirm removal of unnecessary space characters: 
--       leading, trailing, and double spaces in location column
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    location LIKE '% '
    OR location LIKE ' %'
    OR location LIKE '%  %';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    location LIKE '% '
    OR location LIKE ' %'
    OR location LIKE '%  %';


--ICV_4: Confirm removal of unnecessary space characters: 
--       leading, trailing, and double spaces in dish_name column
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    dish_name LIKE '% '
    OR dish_name LIKE ' %'
    OR dish_name LIKE '%  %';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    dish_name LIKE '% '
    OR dish_name LIKE ' %'
    OR dish_name LIKE '%  %';


--ICV_5: Confirm removal of leading ellipses, greater than, less than, 
--       as well as leading or trailing comma, colon, semi-colon, dash, 
--       asterisk, or ampersand characters in the location column
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    location LIKE '...%'
    OR location LIKE '<%'
    OR location LIKE '>%'
    OR location LIKE ',%'
    OR location LIKE '%,'
    OR location LIKE ':%'
    OR location LIKE '%:'
    OR location LIKE ';%'
    OR location LIKE '%;'
    OR location LIKE '-%'
    OR location LIKE '%-'
    OR location LIKE '*%'
    OR location LIKE '%*'
    OR location LIKE '&%'
    OR location LIKE '%&';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    location LIKE '...%'
    OR location LIKE '<%'
    OR location LIKE '>%'
    OR location LIKE ',%'
    OR location LIKE '%,'
    OR location LIKE ':%'
    OR location LIKE '%:'
    OR location LIKE ';%'
    OR location LIKE '%;'
    OR location LIKE '-%'
    OR location LIKE '%-'
    OR location LIKE '*%'
    OR location LIKE '%*'
    OR location LIKE '&%'
    OR location LIKE '%&';


--ICV_6: Confirm removal of leading ellipses, quote, greater than, less than, 
--       as well as leading or trailing comma, colon, semi-colon, dash, 
--       asterisk, or ampersand characters in the dish_name column
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    dish_name LIKE '...%'
    OR dish_name LIKE '<%'
    OR dish_name LIKE '>%'
    OR dish_name LIKE ',%'
    OR dish_name LIKE '%,'
    OR dish_name LIKE ':%'
    OR dish_name LIKE '%:'
    OR dish_name LIKE ';%'
    OR dish_name LIKE '%;'
    OR dish_name LIKE '-%'
    OR dish_name LIKE '%-'
    OR dish_name LIKE '*%'
    OR dish_name LIKE '%*'
    OR dish_name LIKE '&%'
    OR dish_name LIKE '%&';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    dish_name LIKE '...%'
    OR dish_name LIKE '<%'
    OR dish_name LIKE '>%'
    OR dish_name LIKE ',%'
    OR dish_name LIKE '%,'
    OR dish_name LIKE ':%'
    OR dish_name LIKE '%:'
    OR dish_name LIKE ';%'
    OR dish_name LIKE '%;'
    OR dish_name LIKE '-%'
    OR dish_name LIKE '%-'
    OR dish_name LIKE '*%'
    OR dish_name LIKE '%*'
    OR dish_name LIKE '&%'
    OR dish_name LIKE '%&';


--ICV_7: Confirm clustering for removal of duplicates in Menu.location
SELECT COUNT(DISTINCT location)
FROM MenuClean;

SELECT COUNT(DISTINCT location)
FROM MenuRaw;


--ICV_8: Confirm clustering for removal of duplicates in Dish.name
SELECT COUNT(DISTINCT name)
FROM DishClean;

SELECT COUNT(DISTINCT name)
FROM DishRaw;


--ICV_9: Confirm removal of invalid values in location column:
--       where location or restaurant name is not provided
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    location LIKE '%Not Given%'
    OR location LIKE '%not given%'
    OR location LIKE '%Not given%'
    OR location LIKE '%not Given%'
    OR location = 'Unknown';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    location LIKE '%Not Given%'
    OR location LIKE '%not given%'
    OR location LIKE '%Not given%'
    OR location LIKE '%not Given%'
    OR location = 'Unknown';


--ICV_10: Confirm removal of invalid characters in dish_name values: 
--        containing variations of ‘(to order)’
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    dish_name LIKE '%(to order)%'
    OR dish_name LIKE '%(To Order)%'
    OR dish_name LIKE '%(To order)%'
    OR dish_name LIKE '%(to Order)%'
    OR dish_name LIKE '%(TO ORDER)%';

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    dish_name LIKE '%(to order)%'
    OR dish_name LIKE '%(To Order)%'
    OR dish_name LIKE '%(To order)%'
    OR dish_name LIKE '%(to Order)%'
    OR dish_name LIKE '%(TO ORDER)%';


--ICV_11: Confirm that newly added MenuClean.if_NY column includes 
--        only boolean TRUE/FALSE values
SELECT DISTINCT if_NY
FROM MenuClean;


--ICV_12: Entries with invalid or null data filtered out of joint dataset
SELECT COUNT(mi_price)
FROM MenuAggClean
WHERE
    location IS NULL
    OR location = 'Unknown'
    OR dish_name IS NULL
    OR mi_price <= 0;

SELECT COUNT(mi_price)
FROM MenuAggRaw
WHERE
    location IS NULL
    OR location = 'Unknown'
    OR dish_name IS NULL
    OR mi_price <= 0;