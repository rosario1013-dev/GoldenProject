import pandas, bs4, random
import numpy as np
from prettytable import PrettyTable
from IPython.display import HTML

class Table:
    def __init__(self):
        self.items = []

    def Item(self, items):
        if type(items) == list:
            for e in items:
                self.items.append(e.copy())
        else:
            self.items.append(items.copy())
        return self

    def value(self, st):
        result = {'propert': {}}
        for item in self.items:
            result['propert'][item.ID] = item.proprty()
            s = item.value(st)
            for dt in s.index:
                if dt not in result: 
                    result[dt] = {}
                result[dt][item.ID] = s[dt]

        return pandas.DataFrame(result).T.sort_index(ascending=False).T
    def get_df(self, st):
        df = self.value(st)
        return df

    def tabletag(self, st):
        df = self.value(st)
        # tbl = bs4.BeautifulSoup("<table><thead></thead><tbody></tbody></table>", 'html.parser')
        tbl = bs4.BeautifulSoup("<table><thead><tr></tr></thead><tbody></tbody></table>", 'html.parser')

        # # title추가부분
        # titletr = tbl.new_tag("tr"); tbl.thead.append(titletr)
        # title = tbl.new_tag("td"); titletr.append(title)
        # title.string = '流动资产'
        # hearder추가부분
        thead = tbl.new_tag("tr"); tbl.thead.append(thead)
        nth = tbl.new_tag("th"); thead.append(nth)
        nth.string = "项目"; 
        nth['class'] = ["d-inline-block varname"]
        # nth['style'] = ["min-width: 250px"]

        cols = list(df.columns)
        cols.pop(0)
        for col in cols:
            nth = tbl.new_tag("th"); thead.append(nth)
            nth.string = col;
            if col[4:] == '-12-31': 
                nth['class'] = ["Yend"]

        # body추가부분
        tbody = tbl.tbody
        for item in self.items:
            tbody.append(item.rowtag(st))
        return tbl.prettify()

    def table(self, st):
        style = """
            <style>
                .rendered_html table { 
                    border: 3px solid black; 
                    padding: .1rem;
                }
                .rendered_html thead th {
                    text-align: center;
                    min-width: 120px;

                }
                .rendered_html td, rendered_html th {
                    padding: .1rem;
                }

                .rendered_html .varname { 
                    background: bisque; 
                    min-width: 400px;
                    text-align: left;
                    border-right: 3px solid black; 
                }
                .rendered_html .Yend{
                    background: gainsboro;
                    border-color: floralwhite;
                }
                .rendered_html .item_h1{
                    color: cornflowerblue;
                    background: gainsboro
                }
                .rendered_html .ind2{
                    text-indent: 4ch !important;
                }
                .rendered_html .ck{
                    font-style: italic;
                }

            </style> 
        """
        return HTML(style + self.tabletag(st))

    def renderHTML(self, st):
        style = """
            <style>
                .table { 
                    border: 2px solid black; 
                    padding: .1rem;
                }
                .thead th {
                    text-align: center;
                    min-width: 120px;
                    border: black 1px solid;
                }
                td, th {
                    padding: .1rem; 
                    border: black 1px solid;
                    text-align: right;
                }
                th {
                    padding: .1rem; 
                    border: black 1px solid;                    
                }
                .varname { 
                    background: bisque; 
                    min-width: 400px;
                    text-align: left;
                    border: black 1px solid;

                }
                .Yend{
                    background: gainsboro;
                    border: black 1px solid;
                }
            </style> 
        """
        return style + self.tabletag(st)