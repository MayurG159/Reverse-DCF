import streamlit as st
from bs4 import BeautifulSoup as bs
import requests
import pandas as pd
import cufflinks as plot
import statistics as stat

st.header('VALUING CONSISTENT COMPOUNDERS')
st.write('Hi there!')
st.write('This page will help you calculate intrinsic PE of consistent compounders through growth-RoCE DCF model.')
st.write('We then compare this with current PE of the stock to calculate degree of overvaluation.')
a = st.text_input(label='NSE/BSE symbol', value='TATAMOTORS')
if a:
    sym = a.upper().strip()

# Sliders
Cost_of_cap1 = st.select_slider(label="Cost of Capital (CoC): %", options=(list(range(8, 17))),value=11)
RoCE1 = st.select_slider(label="Return on Capital Employed (RoCE): %", options=(list(range(10, 110, 10))),value=30)
high_growth_rate1 = st.select_slider(label="Growth during high growth period: $", options=(list(range(8, 21, 2))),value=14)
high_growth_period1 = st.select_slider(label="High Growth Period(Years)", options=((list(range(10, 26, 2))) + [25]),value=18)
Fade_period1 = st.select_slider(label="Fade period(years):", options=((list(range(5, 25, 5))) + [25]),value=20)
Terminal_growth_rate1 = st.select_slider(label="Terminal growth rate: %", options=((list(range(0, 8))) + [7.5]),value=4)

def perc_value(a):
    return a/100
def get_soup(url):
    response = requests.get(url)
    if response.status_code == 200:
        return bs(response.text, 'html.parser')
    else:
        raise Exception(f"Failed to fetch data from {url}")


def extract_data(symbol):
    consolidated_url = f'https://www.screener.in/company/{symbol}/consolidated/'
    soup = get_soup(consolidated_url)

    ROCE_value = soup.find('div', class_='card card-large').find('div', class_='company-info').find('div', class_='company-ratios').find_all('li', class_='flex flex-space-between')[6].find('span', class_='nowrap value').span.text.strip().replace('\n', '')

    if ROCE_value == '':
        print("Consolidated data not available. Falling back to standalone data.")
        standalone_url = f'https://www.screener.in/company/{symbol}/'
        soup = get_soup(standalone_url)

    data = extract_summary_data(soup)
    year_profit = extract_profit_data(soup)
    Comp_sales_year, Comp_sales_values = extract_compounded_growth_data(soup, 0)
    Comp_profit_year, Comp_profit_values = extract_compounded_growth_data(soup, 1)
    median = extract_roce_data(soup)

    return data, year_profit, Comp_sales_year, Comp_sales_values, Comp_profit_year, Comp_profit_values, median


def extract_summary_data(soup):
    summaries = soup.find_all('li', class_='flex flex-space-between')
    data = {}
    for summary in summaries:
        summary_name = summary.find('span', class_='name').text.replace(' ', '').replace('\n', '')
        value = float(summary.find('span', class_='nowrap value').span.text.replace(',', '').replace(' ', ''))
        data[summary_name] = value
    return data


def remove_month_from_keys(dictionary):
    months = ['Jan ', 'Feb ', 'Mar ', 'Apr ', 'May ', 'Jun ', 'Jul ', 'Aug ', 'Sep ', 'Oct ', 'Nov ', 'Dec ']
    for month in months:
        dictionary = {key.replace(month, ''): value for key, value in dictionary.items()}
    return dictionary


def extract_profit_data(soup):
    Year_Profit = {}
    Profit_loss_section = soup.find("section", id='profit-loss')
    table_access = Profit_loss_section.find('div', class_='responsive-holder fill-card-width')
    main_table = table_access.find('table', class_='data-table responsive-text-nowrap')
    Year = (main_table.thead.tr.text.strip().replace('Dec ', '')).split('\n')
    Net_Profits_YEAR = (((main_table.find('tbody')).find_all('tr', class_='strong')[2].text.replace(' ', '').replace(
        ',', '').replace('NetProfit +', '').strip())).split('\n')
    for i in range(len(Year)):
        Year_Profit[Year[i]] = Net_Profits_YEAR[i]
    y = Year_Profit
    # Remove months from keys
    year_profit = remove_month_from_keys(y)
    return year_profit


def extract_compounded_growth_data(soup, table_index):
    Comp_year = []
    Comp_values = []
    Table = soup.find_all('table', class_='ranges-table')[table_index]
    data = Table.find_all('td')
    for i in range(0, 8):
        value = data[i].text
        if 'Years' in value:
            Comp_year.append(value.replace(':', '').replace('Years', 'YRS'))
        elif 'TTM' in value:
            Comp_year.append(value.replace(':', ''))
        else:
            Comp_values.append(int(value.replace('%', '')))
    return Comp_year, Comp_values


def extract_roce_data(soup):
    ROCE_yr = ((((soup.find('section', id='ratios').find('table', class_='data-table responsive-text-nowrap').find('tbody')).find_all('tr')[5].text.strip().replace(' ', '').replace(',', ''))).replace('%', '').replace('\n\n','')).split('\n')
    ROCE_yr.remove('ROCE')
    ROCE_yr = [int(value) for value in ROCE_yr]
    ROCE_yr_5yrs = ROCE_yr[-5:]
    median = stat.median(ROCE_yr_5yrs)
    return median


def intrinsic_PE(Cost_of_cap, RoCE, high_growth_rate, high_growth_period, Fade_period, Terminal_growth_rate):
    tax_rate = 0.25  # perc_value(25)
    COC = perc_value(Cost_of_cap)
    high_grw_rate = perc_value(high_growth_rate)
    terminal_grw_rate = perc_value(Terminal_growth_rate)
    fade_period = Fade_period
    ROC_Pre_tax = perc_value(RoCE)
    ROC_Post_tax = ROC_Pre_tax * (1 - (tax_rate))
    Reinvestment_rate_1 = ((high_grw_rate) / ROC_Post_tax)
    Reinvestment_rate_2 = (terminal_grw_rate) / ROC_Post_tax

    capital_ending_1 = [100]
    NOPAT_1 = []
    inv_1 = []
    EBT = []
    FCF = []
    discount_factor = []
    discounted_FCF = []
    Earnings_Grw = []

    for i in range(0, ((high_growth_period + fade_period) + 2)):
        if i > 0:
            NOPAT_1.append(capital_ending_1[i - 1] * ROC_Post_tax)
            if i > 1:
                if len(NOPAT_1) > 1:
                    if (i - 2) < 16:
                        Earnings_Grw.append(
                            ((((NOPAT_1[i - 1] / NOPAT_1[i - 2]) - 1) * 100).__round__(0)))
                    elif (i - 2) == 16:
                        Earnings_Grw.append(
                            ((perc_value(Earnings_Grw[10]) - (((high_grw_rate) - (terminal_grw_rate)) / fade_period)) * 100))
                    else:
                        Earnings_Grw.append(
                            ((perc_value(Earnings_Grw[i - 3]) - (((high_grw_rate) - (terminal_grw_rate)) / fade_period)) * 100))
                else:
                    pass

            if (i - 1) < 16:
                inv_1.append(NOPAT_1[i - 1] * Reinvestment_rate_1)
                capital_ending_1.append(inv_1[i - 1] + capital_ending_1[i - 1])
            else:
                inv_1.append(
                    (perc_value(Earnings_Grw[i - 2]) / ROC_Post_tax) * NOPAT_1[i - 1])
                capital_ending_1.append(inv_1[i - 1] + capital_ending_1[i - 1])

            EBT.append((NOPAT_1[i - 1] / (1 - (tax_rate))))
            FCF.append(((NOPAT_1[i - 1]) - inv_1[i - 1]))
            discount_factor.append((1 / ((1 + (COC)) ** (i - 1))))
            discounted_FCF.append((FCF[i - 1] * discount_factor[i - 1]).__round__(0))

    Terminal_NOPAT = (NOPAT_1[len(NOPAT_1) - 1] * (1 + terminal_grw_rate) / ((COC) - (terminal_grw_rate)))
    Terminal_inv = (Terminal_NOPAT) * ((Reinvestment_rate_2))
    Terminal_FCF = Terminal_NOPAT - Terminal_inv
    Terminal_dis_factor = discount_factor[len(discount_factor) - 1]
    Terminal_dis_FCF = (Terminal_FCF) * (Terminal_dis_factor)

    intrinsic_value = (sum(discounted_FCF) + Terminal_dis_FCF)
    intrinsic_PE = intrinsic_value / NOPAT_1[0]
    return intrinsic_PE

def overvaluation(current_pe,FY23PE,intrinsicPE):
    if current_pe < FY23PE :
        val = (((current_pe/intrinsicPE)-1)*100)
        return val
    else :
        val = (((FY23PE/intrinsicPE)-1)*100)
        return val


if __name__ == "__main__":
    data, year_profit, Comp_sales_year, Comp_sales_values, Comp_profit_year, Comp_profit_values, median = extract_data(sym)
    st.write('Stock Symbol: ', sym)
    st.write('Current PE: ' + str(data.get('StockP/E', 'N/A')))
    st.write('FY23PE:' + str(round((data['MarketCap'] / float(year_profit['2022'])), 1)))
    st.write('5-yr median pre-tax RoCE: ' + str(median), '% \n')

    sales_df = pd.DataFrame({'Years': Comp_sales_year, 'Growth': Comp_sales_values})
    profit_df = pd.DataFrame({'Years': Comp_profit_year, 'Growth': Comp_profit_values})
    col_1,col_2 = st.columns(2)
    with col_1:
        st.write('Sales Growth')
        st.write(sales_df.transpose())
    with col_2:
        st.write('Profit Growth')
        st.write(profit_df.transpose())

    plot.go_offline()
    col1, col2 = st.columns(2)
    with col1:
        st.header('Sales growth')
        st.bar_chart(sales_df, x='Years', y='Growth')
    with col2:
        st.header('Profit growth')
        st.bar_chart(profit_df, x='Years', y='Growth')

    # Calculate intrinsic PE
    value = intrinsic_PE(Cost_of_cap1, RoCE1, high_growth_rate1, high_growth_period1, Fade_period1,Terminal_growth_rate1)
    st.write('Play with inputs to see changes in intrinsic PE and overvaluation:')
    st.write("The calculated intrinsic PE is: " + str(value))
    overval = (overvaluation(data.get('StockP/E', 'N/A'),(data['MarketCap'] / float(year_profit['2022'])),value)).__round__(2)
    st.write("Degree of overvaluation:  "+ str(overval) + " %")


