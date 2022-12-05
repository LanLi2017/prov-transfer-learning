DROP TABLE IF EXISTS menu;
CREATE TABLE menu(
  "id" BIGINT,
  "name" TEXT,
  "sponsor" TEXT,
  "event" TEXT,
  "venue" TEXT,
  "place" TEXT,
  "physical_description" TEXT,
  "occasion" TEXT,
  "notes" TEXT,
  "call_number" TEXT,
  "keywords" TEXT,
  "language" TEXT,
  "date" TEXT,
  "location" TEXT,
  "location_type" TEXT,
  "currency" TEXT,
  "currency_symbol" TEXT,
  "status" TEXT,
  "page_count" INT,
  "dish_count" INT,
  PRIMARY KEY(id)
);

DROP TABLE IF EXISTS dish;
CREATE TABLE dish(
  "id" BIGINT,
  "name" TEXT,
  "description" TEXT,
  "menus_appeared" INT,
  "times_appeared" INT,
  "first_appeared" INT,
  "last_appeared" INT,
  "lowest_price" DOUBLE,
  "highest_price" DOUBLE,
  PRIMARY KEY(id)
);

DROP TABLE IF EXISTS menupage;
CREATE TABLE menupage(
  "id" BIGINT,
  "menu_id" BIGINT,
  "page_number" INT,
  "image_id" INT,
  "full_height" INT,
  "full_width" INT,
  "uuid" TEXT,
  PRIMARY KEY(id),
  FOREIGN KEY (menu_id) REFERENCES menu(id)
);

DROP TABLE IF EXISTS menuitem;
CREATE TABLE menuitem(
  "id" BIGINT,
  "menu_page_id" BIGINT,
  "price" DOUBLE,
  "high_price" DOUBLE,
  "dish_id" BIGINT,
  "created_at" DATETIME,
  "updated_at" DATETIME,
  "xpos" DOUBLE,
  "ypos" DOUBLE,
  PRIMARY KEY(id),
  FOREIGN KEY (menu_page_id) REFERENCES menupage(id),
  FOREIGN KEY (dish_id) REFERENCES dish(id)
);

.mode csv
.import /root/Menu_clean/without_header/Menu.csv menu
.import /root/Menu_clean/without_header/Dish.csv dish
.import /root/Menu_clean/without_header/MenuItem.csv menuitem
.import /root/Menu_clean/without_header/MenuPage.csv menupage

