##### FUNÇÕES_Restrições pulp
import warnings
warnings.filterwarnings("ignore")

def sol_excludentes(dfsolucoes, sol_vars, banda, portadora, s):
        restricao = 0
        filter_banda = dfsolucoes[dfsolucoes['Banda']==banda]
        filter_port = filter_banda[filter_banda['Portadora']==portadora]
        check_mMIMO = set(filter_port['Grupo_Solucao'])

        if ('mMIMO' in check_mMIMO): #(s != 0):
                lista_sol_check = list(filter_port[filter_port['Grupo_Solucao']!='mMIMO'].index.unique())
                lista_sol_mMIMO = list(filter_port[filter_port['Grupo_Solucao']=='mMIMO'].index.unique())
                for i in lista_sol_mMIMO:
                        if 'S'+str(s) in i:
                                lista_sol_mMIMO_s = lista_sol_check
                                lista_sol_mMIMO_s.append(i)
                                restricao = sum(sol_vars[sol_check] for sol_check in lista_sol_check)   
        elif (s == 0):
                lista_sol_check = list(filter_port.index.unique())
                restricao = sum(sol_vars[sol_check] for sol_check in lista_sol_check)     
        return restricao

    
def listaFiltro(dataframe, valores):
    return dataframe.loc[dataframe['End_id'].isin(valores)]
