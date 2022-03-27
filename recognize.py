import datetime
import functools
import re
import pandas as pd
import streamlit as st
import requests

from PIL import Image
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

im = Image.open("RePharma-transparent.png")
st.set_page_config(page_title="RePharma", page_icon=im)

img, _, title = st.columns([0.1, 0.1, 0.9])
img.image(im, width=100)


@st.experimental_singleton(show_spinner=False)
def current_enabled_pharma_list():
    return pd.read_csv('https://ogyei.gov.hu/generalt_listak/tk_lista.csv', sep=';', encoding='ISO-8859-2').filter(
        regex='Név|Kiszerelés')


@st.experimental_singleton
def get_registered_pharma_list():
    return pd.DataFrame(columns=['Barcode', 'Name', 'Quantity', 'Left quantity', 'Unit', 'Expiry date'])


@st.experimental_memo(show_spinner=False)
def get_pharma_information(barcode):
    url = "https://google-search3.p.rapidapi.com/api/v1/search/q=site:https://pingvinpatika.hu%20" + barcode

    headers = {
        "X-User-Agent": "mobile",
        "X-Proxy-Location": "EU",
        "X-RapidAPI-Host": "google-search3.p.rapidapi.com",
        "X-RapidAPI-Key": st.secrets['API_KEY']
    }

    with st.spinner("Searching for the product..."):
        response = requests.request("GET", url, headers=headers).json()['results']

        if response:
            return response[0]['title'].split(' - ')[0].strip(), \
                   requests.request("GET", response[0]['link']).text.split('Kiszerelés:')[1].split('</div>')[0].split(
                       '>')[-1]

        else:
            url = "https://google-search3.p.rapidapi.com/api/v1/search/q=site:https://egeszsegpalace.hu%20" + barcode

            response = requests.request("GET", url, headers=headers).json()['results']

            if response:
                return response[0]['title'].split(' - ')[0].strip(), \
                       requests.request("GET", response[0]['link']).text.split('Kiszerelés: ')[1].split('<')[0].strip()
            else:
                return None, None



with st.spinner("Downloading marketed medicine list (in Hungary)..."):
    all_list = current_enabled_pharma_list()
df = get_registered_pharma_list()

additional_page = not st.experimental_get_query_params().get("p", "")

if additional_page:
    title.title("RePharma admission form")


    line_wr = st.empty()
    content = st.container()
    restart = st.empty()

    if restart.button("New product"):
        st.session_state.ean = ""
        st.session_state.name_from_list = ""

    line_ctn = line_wr.container()
    name_from_list = line_ctn.selectbox("Pharma name from list", ["", *all_list[all_list.columns].agg(' - '.join, axis=1)], key="name_from_list")

    line = line_ctn.text_input("EAN number", key="ean").strip().replace('ö', '0')

    with content:
        if name_from_list or line:
            if name_from_list:
                name, quantity = name_from_list.split(' - ', 1)
            elif line:
                name, quantity = get_pharma_information(line)
            else:
                name = None

            if name:
                line_wr.empty()
                name_c, quantity_c = st.columns([0.8, 0.2])
                name_c.subheader("Name")
                name_c.write(name)
                quantity_c.subheader("Quantity")
                quantity_c.write(quantity)

                max_quantity = int(functools.reduce(lambda i, j: float(i) * float(j), re.findall(r'[\d.]+', quantity)))

                today = datetime.date.today()

                with st.form(key="form"):
                    expiry_date = st.date_input("Expiry date", min_value=today)

                    quantity_c, unit_of_measurement_c = st.columns([0.75, 0.25])
                    left_quantity = quantity_c.selectbox("Quantity left in product", reversed(range(1, max_quantity+1)), key='quantity')
                    default_unit = 1 if 'ml' in quantity else 2 if 'g' in quantity else 0
                    unit_of_measurement = unit_of_measurement_c.selectbox("Unit of measurement", ['piece(s)', 'ml', 'gram(s)'], index=default_unit,
                                                                          key='mertekegyseg', disabled=bool(default_unit))

                    if st.form_submit_button("Submit"):
                        df.loc[len(df.index)] = [line, name, quantity, left_quantity, unit_of_measurement, expiry_date.strftime("%m-%Y")]
                        st.success("Product has been added to the list!")

            else:
                st.warning("No information found")
        else:
            restart.empty()

    df_tr = df.filter(['Name', 'Quantity', 'Left quantity', 'Unit', 'Expiry date']).sort_values('Expiry date')
    gridOptions = None
    update = GridUpdateMode.NO_UPDATE
else:
    title.title("RePharma GP selector form")

    st.button("GET")

    df_tr = df.filter(['Name', 'Quantity', 'Left quantity', 'Unit', 'Expiry date']).sort_values('Expiry date')

    @st.experimental_memo
    def get_grid_options():
        gb = GridOptionsBuilder.from_dataframe(df_tr)
        gb.configure_selection(selection_mode='multiple', use_checkbox=True)
        return gb.build()


    gridOptions = get_grid_options()
    update = GridUpdateMode.SELECTION_CHANGED

g = AgGrid(df_tr,
       gridOptions=gridOptions,
       reload_data=True,
       update_mode=update,
       fit_columns_on_grid_load=True,
       key='aggrid')

if not additional_page:
    was = False
    for selected in g["selected_rows"]:
        for ith in df[(df['Name'] == selected['Name']) & (df['Quantity'] == selected['Quantity']) &
               (df['Left quantity'] == selected['Left quantity']) & (
                       df['Expiry date'] == selected['Expiry date'])].iterrows():
            df.drop(ith[0], inplace=True)
            was = True
    if was:
        st.experimental_rerun()
