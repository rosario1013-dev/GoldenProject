from GP_KDB import KDB
import pandas, numpy, bs4
from prettytable import PrettyTable
from IPython.display import HTML
from GP_FSA import accounts


class Acc(object):

    def __init__(self, ID):
        self.ID = ID
        self.cn = ID
        self.en = ID
        self.children = []
        self.children_eff = {}
        self.isPercent = False
        accounts[self.ID] = self
        self.col = ''
        self.unit = 1
        self.color = 'blue'

    def __repr__(self):
        return f"➢【Acc】{self.ID}, 단위={self.unit}, 계시={self.col}"

    def Col(self, col):
        self.col = col
        return self

    def En(self, en):
        self.en = en
        return self    

    def U(self, unit=10000):
        self.unit = unit
        return self

    def Child(self, child):
        self.children.append(child)
        self.children_eff[child] = 1

    def get_cols(self):
        result = {
            'cols':['IDE', 'REPORTDATE', self.col],
            'names': {self.col:self.ID}
        }
        if len(self.children) > 0:
            for child in self.children:
                result['cols'].append(child.col)
                result['names'][child.col] = child.ID
        return result



    def value(self, st):
        if not hasattr(st, 'FS'): 
            raise Exception('Stock({}) has not FS table.'.format(st.IDE))
        return st.FS[self.col] * self.unit

    def table(self, st):
        val = self.value(st)
        tbl = PrettyTable()
        tbl.add_column("REPORTDATE", list(val.index))
        tbl.add_column(self.ID, list(val))
        tbl.align[self.ID] = "r"
        tbl.border = True
        tbl.header = True
        tbl.padding_width = 5
        tbl.format = True
        tbl.float_format = '0.2'
        tblstr = tbl.get_html_string(
            attributes={"REPRTDATE":"my_table", "class":"red_table"}
        )
        return HTML(tblstr)

    def rowtag(self, st):
        val = self.value(st).sort_index(ascending=False)

        tbl = bs4.BeautifulSoup("<table></table>", 'html.parser')
        tr = tbl.new_tag("tr")
                
        # 항목이름부
        td = tbl.new_tag("td");  tr.append(td)
        td.string = self.ID 
        td['style'] = []
        if hasattr(self, 'taglevel'):
            td['style'].append(f'text-indent: {self.taglevel*30}px;font-weight: bold;')
        
        if hasattr(self, 'color'):
            td['style'].append(f'color: {self.color};')


        td['class'] = ["d-inline-block varname"]

        if hasattr(self, 'tagName'):
            td.string = self.tagName
        
        
        # 항목수자부
        numberstyle = []
        if hasattr(self, 'color'):
            numberstyle.append(f'color: {self.color};')

        for dt in val.index:
            td = tbl.new_tag("td");  tr.append(td)
            if len(numberstyle) > 0:
                td['style'] = numberstyle

            if numpy.isnan(val[dt]):  
                td.string = "--"
            elif val[dt] == 0: 
                td.string = "0"
            else: 
                td.string = format(val[dt], '0.2f');

            if dt[4:] == '-12-31':  td['class'] = ["Yend"]
        return tr

    def proprty(self):
        result = {}
        if hasattr(self, 'taglevel'):
            result['taglevel'] = self.taglevel
        if hasattr(self, 'color'):
            result['color'] = self.color
        if hasattr(self, 'tagName'):
            result['tag'] = self.tagName
        if hasattr(self, 'isPercent'):
            result['isPercent'] = self.isPercent
        return result

    def copy(self):
        n = self.__new__(self.__class__)
        n.__dict__.update(**self.__dict__)
        return n

    def tag_level(self, lev):
        self.taglevel = lev
        return self

    def tag_Name(self, name):
        self.tagName = name
        return self

    def Color(self, color):
        self.color = color
        return self

    def Percent(self):
        self.isPercent = True
        return self

    def table_column(self, columnstyledict):
        self.tablecolumn = columnstyledict
        return self

def Regist_this_to_account_list(ntup):
    if type(ntup[0]) == str:
        ID = ntup[0]
        col = ntup[1]
        newAccount = Acc(ID).Col(col)
        if len(ntup) < 3: 
            return newAccount
        if type(ntup[2]) == list:
            for e in ntup[2]: 
                res = Regist_this_to_account_list(e)
                if type(res) == Acc:
                    newAccount.Child(res)
                elif type(res) == tuple:
                    newAccount.Child(res[0])
                    newAccount.children_eff[res[0]] = res[1]
            return newAccount
                    
        elif type(ntup[2]) == int:
            newAccount.U(ntup[2])
            try:
                if type(ntup[3]) == list:
                    for e in ntup[3]: 
                        newAccount.Child(Regist_this_to_account_list(e))
            except:
                pass

    elif type(ntup[0]) == Acc:
        if len(ntup) == 1: return ntup[0]
        elif len(ntup) == 2:
            if ntup[1] in [1, -1]:

                newAccount = ntup[0].copy()
                newAccount.unit = ntup[1] * newAccount.unit
                # print(newAccount)
                return newAccount
    else:
        raise Exception('Account의 정의형식이 맞지 않는다.')
    return newAccount

