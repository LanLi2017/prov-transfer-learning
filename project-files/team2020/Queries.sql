-- Integrity constraint checks for dish -- 
-- PRIMARY KEY constraints
SELECT Count(id)
FROM   dish
WHERE  id IS NULL;

SELECT count(id) FROM
  (SELECT id, count(id)
  FROM dish
  GROUP BY id
  HAVING count(id) > 1);

-- NOT NULL constraint checks
SELECT count(name)
FROM dish
WHERE name IS NULL OR
name = "";

-- Fix Integrity constraint violations for dish -- 
-- Delete rows with NULL P.K
DELETE FROM dish
WHERE id IN (SELECT id FROM dish
             WHERE id IS NULL);

-- Delete rows with duplicate id.
DELETE FROM dish
WHERE id IN (SELECT id FROM
              (SELECT id, count(id) FROM dish
                GROUP BY id
                HAVING count(id) > 1)
            );

-- Delete rows with NULL or empty name.
SELECT count(name)
FROM dish
WHERE name IS NULL OR
name = "";

-- Integrity constraint checks for menu -- 
-- PRIMARY KEY constraints
SELECT Count(id)
FROM   menu
WHERE  id IS NULL;

SELECT count(id) FROM
  (SELECT id, count(id)
  FROM menu
  GROUP BY id
  HAVING count(id) > 1);

-- data integrity constraints
SELECT count(id)
FROM menu
WHERE (date < 1700 or date > 2021)
AND date IS NOT NULL
AND date != ''

NOT NULL constraint checks
SELECT count(name)
FROM menu
WHERE name IS NULL OR name = "";

SELECT count(event)
FROM menu
WHERE event IS NULL OR event = "";

SELECT count(occasion)
FROM menu
WHERE occasion IS NULL OR occasion = "";

-- Fix Integrity constraint violations for menu -- 
DELETE FROM menu
WHERE id IN (
  SELECT id
  FROM  menu
  WHERE  (date < 1700 OR date > 2021 )
          AND date != ""
  );

-- Integrity constraint checks for menuitem -- 
-- PK check
SELECT Count(id)
FROM   dish
WHERE  id IS NULL;

-- FK check
SELECT count(id)
FROM menuitem
WHERE dish_id NOT IN (SELECT id FROM dish);

SELECT count(id)
FROM menuitem
WHERE menu_page_id NOT IN (SELECT id FROM menupage);

-- Fix Integrity constraint violations for menuitem -- 
DELETE FROM menuitem
WHERE id IN (
  SELECT id FROM menuitem
  WHERE dish_id NOT IN (SELECT id FROM dish)
);

DELETE FROM menuitem
WHERE id IN (
  SELECT id FROM menuitem
  WHERE menu_page_id NOT IN (SELECT id FROM menupage)
);

-- Integrity constraint checks for menupage -- 
-- PRIMARY KEY constraints
SELECT Count(id)
FROM   menupage
WHERE  id IS NULL;

SELECT id, count(id)
FROM menupage
GROUP BY id
HAVING count(id) > 1;

-- REFERENTIAL INTEGRITY constraints
SELECT count(id)
FROM menupage
WHERE menu_id IS NULL;

SELECT count(id)
FROM menupage
WHERE menu_id NOT IN (SELECT id FROM menu);

-- Fix Integrity constraint violations for menupage -- 
--Delete rows where menu_id does not exist in menu
DELETE FROM menupage
WHERE id in (SELECT id
  FROM menupage
  WHERE menu_id NOT IN (SELECT id FROM menu)
);

