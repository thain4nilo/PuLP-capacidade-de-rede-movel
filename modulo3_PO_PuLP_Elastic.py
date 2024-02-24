########################################################
# MODULO 3 - Definir melhor solução para o Endereço ID #
########################################################
# Inputs necessários:
# -Planilha de levantamento do estado atual da rede: soluções já disponíveis no end_id
# -Planilha de custos x capacidade da solução: capacidade, custo para cada solução e grupo/categoria na qual esta pertence (LAYER, mMIMO)
# -Planilha de restrições: soluções possíveis de serem implantadas por end_id, levando em consideração: biosite, banda p, refarming
# -Planilha de capacidade necessária: PRB necessário para colocar end_id na meta
# Outputs:
# -Planilha com endereço Id e solução sugerida indicando também eventuais penalizações para alcançar o target de PRB


#### import de biblioteca #######################################################
from pulp import *
import pandas as pd
import numpy as np
import modulo3_funcoes
import config
import datetime
import warnings
from tqdm import tqdm
warnings.filterwarnings("ignore")


def main():
    print('-' * 60)
    config.PrintComHora('Executando Modulo 3...')
    #### import de dataframes #######################################################
    ## DF de universo de END_IDs 
    lista_endids = pd.read_excel(config.__LISTA_ENDIDs)
    lista_endids = list(lista_endids['END_ID'])

    ## Planilha de levantamento do estado atual da rede
    df_rede = pd.read_excel(config.__ARQUIVO_LEVANTAMENTO_DA_REDE)
    df_rede.rename({'Endereço ID':'End_id'},axis=1, inplace= True) #Renomeando Endereço ID para End_id
    #df_rede = modulo3_funcoes.listaFiltro(df_rede, lista_endids)
    #lista_endids = list(df_rede['End_id'])
    df_rede.set_index('End_id', inplace=True) #Setando End_id como identificador das linhas
    
    ## Planilha de Custo x Capacidade da solução
    df_solucoes = config.df_solucoes_original.copy(deep=True) #copiando solucoes do modulo config importado
    grupo_solucoes = df_solucoes[['Solucao','Grupo_Solucao']].set_index('Grupo_Solucao') #Criando um dicionário para grupo/categoria de soluções
    lista_grupo_solucoes = (grupo_solucoes.index.unique()) #Criar lista de grupos de soluções existentes
    solucoes_itens = list(df_solucoes['Solucao']) #Criar lista de soluções existentes
    df_solucoes.set_index('Solucao', drop=True, inplace=True) #Setando a Solução como identificador das linhas

    ## Planilha de Restrições
    
    df_restricoes = pd.read_excel(config.__ARQUIVO_PLAN_RESTRICOES)
    df_restricoes.rename({'Endereço ID':'End_id'},axis=1, inplace= True) #Renomeando Endereço ID para End_id
    df_restricoes = modulo3_funcoes.listaFiltro(df_restricoes, lista_endids)
    df_restricoes.set_index('End_id', inplace=True) #Setando End_id como identificador das linhas

    #### Preparação de Base Para Pesquisa Operacional #######################################################
    ## Contagem de soluções existentes
    for grupo in lista_grupo_solucoes:
        df_rede[grupo] = 0
    for grupo in lista_grupo_solucoes:
        if len(grupo_solucoes.loc[grupo]) > 1:
            solucoes_no_grupo = list(grupo_solucoes.loc[grupo]['Solucao'])
            df_rede[grupo] = df_rede[solucoes_no_grupo].sum(axis=1)
        else:
            solucoes_no_grupo = grupo_solucoes.loc[grupo]['Solucao']
            df_rede[grupo] = df_rede[solucoes_no_grupo]

    ## Criação da base problema
    # (objetivo: criar uma base que onde houver 1 é possível utilizar aquela solução)
    df_prob = df_restricoes.copy(deep=True) #Construir o df do problema usando como base a o df_restrições (Só serão considerados os End_ids que estiverem na base de restrições)
    for endid in lista_endids:
        for s in solucoes_itens:
            if df_rede.loc[endid,s] == 1:
                df_prob.loc[endid,s] = 0 #Onde houver 1 na base de rede deve-se colocar como solução indisponível na base de problema

    df_prob = df_prob.join(df_rede[lista_grupo_solucoes]) #Adicionar as colunas do df_rede que informam a quantidade de soluções existentes à base problema, index = End_id (apenas os presentes em df_restrições)
    df_prob = df_prob.join(df_rede[['S1','S1_FUTURO','S2','S2_FUTURO','S3','S3_FUTURO','2600_OUTRA_OPERADORA']])

    #### PuLP #######################################################
    df_pulp = pd.DataFrame(columns=['End_id', 'Status', 'Solucoes'])

    for endid in (lista_endids):
        if df_prob.loc[endid,'2600_OUTRA_OPERADORA'] == 0:
            ## Criando o problema
            prob = LpProblem("Determinar solução otima de ampliacao da rede",LpMinimize) #Problema
            sol_vars = LpVariable.dicts("SOLUCOES", solucoes_itens, 0 , 1, cat='Integer') #Cria as variáveis de decisão

                ## Restrições gerais
            sol_possiveis = [] #vetor de soluções possíveis para o end_id
            for s in solucoes_itens: 
                if df_prob.loc[endid,s] == 1:
                    sol_possiveis.append(s)
            if len(sol_possiveis) > 0:
                prob += lpSum([df_solucoes.loc[i,'Custo']*sol_vars[i] for i in sol_possiveis]) #Função objetivo
                
                ## Condição para soluções excludentes
                for banda in list(set(df_solucoes['Banda'])):
                    for portadora in ['P1','P2','P3']:
                        for s in [0,1,2,3]:
                            prob += modulo3_funcoes.sol_excludentes(df_solucoes, sol_vars, banda, portadora, s) <= 1

                ## Condição de solução para Biosite
                if df_prob.loc[endid,'Biosite'] == 1:
                    prob += lpSum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['BANDA','Solucao'])) <= df_prob.loc[endid,'Layers Possiveis']-df_prob.loc[endid,'BANDA']
                    prob += lpSum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['mMIMO','Solucao'])) <= df_prob.loc[endid,'mMIMO POSSIVEL']-df_prob.loc[endid,'mMIMO']
                    prob += lpSum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['MIMO4X4','Solucao'])) <= 0
                    prob += lpSum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['TWIN_BEAM','Solucao'])) <= 0

                ## Subproblema - restrição elástica - Cap Add
                #S1
                S1_LHS = LpAffineExpression([(sol_vars[s], df_solucoes.loc[s,'Cap_Setor1']) for s in sol_possiveis])
                S1_Target = (df_prob.loc[endid, 'S1_FUTURO']-df_prob.loc[endid,'S1'])
                S1_c = LpConstraint(e= S1_LHS, sense=1, name='Cap_Add_S1', rhs=S1_Target)
                S1_elastic = S1_c.makeElasticSubProblem(penalty = config.__PENALIDADE, proportionFreeBound = config.__TOLERANCIA)
                prob.extend(S1_elastic)
                #S2
                S2_LHS = LpAffineExpression([(sol_vars[s], df_solucoes.loc[s,'Cap_Setor2']) for s in sol_possiveis])
                S2_Target = (df_prob.loc[endid, 'S2_FUTURO']-df_prob.loc[endid,'S2'])
                S2_c = LpConstraint(e= S2_LHS, sense=1, name='Cap_Add_S2', rhs=S2_Target)
                S2_elastic = S2_c.makeElasticSubProblem(penalty = config.__PENALIDADE, proportionFreeBound = config.__TOLERANCIA)
                prob.extend(S2_elastic)
                #S3
                S3_LHS = LpAffineExpression([(sol_vars[s], df_solucoes.loc[s,'Cap_Setor3']) for s in sol_possiveis])
                S3_Target = (df_prob.loc[endid, 'S3_FUTURO']-df_prob.loc[endid,'S3'])
                S3_c = LpConstraint(e= S3_LHS, sense=1, name='Cap_Add_S3', rhs=S3_Target)
                S3_elastic = S3_c.makeElasticSubProblem(penalty = config.__PENALIDADE, proportionFreeBound = config.__TOLERANCIA)
                prob.extend(S3_elastic)
                
                ## Resolver o problema
                print(endid, sep=',')
                status = prob.solve()
                

                solucao_pulp = [] # Vetor de soluções
                for v in prob.variables()[9:len(prob.variables())]:
                    if v.varValue > 0:
                        solucao_pulp.append(v.name)
                
                var_status = LpStatus[status]

                ## Repescagem de casos inviáveis que atendem as restrições hard
                if LpStatus[status] == "Infeasible":
                    solucoes_repesc = []
                    for x in solucao_pulp:
                        item = x
                        for y in ['SOLUCOES_']:
                            item = item.replace(y, "")
                        solucoes_repesc.append(item)
                    
                    for x in solucoes_itens:
                        if (x in solucoes_repesc) == False:
                            sol_vars[x] = 0
                        else:
                            sol_vars[x] = 1

                    check_biosite = True 
                    if df_prob.loc[endid,'Biosite'] == 1: 
                        check_biosite = sum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['BANDA','Solucao'])) <= df_prob.loc[endid,'Layers Possiveis']-df_prob.loc[endid,'BANDA']
                        check_biosite = check_biosite and sum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['mMIMO','Solucao'])) <= df_prob.loc[endid,'mMIMO POSSIVEL']-df_prob.loc[endid,'mMIMO']
                        check_biosite = check_biosite and sum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['MIMO4X4','Solucao'])) <= 0
                        check_biosite = check_biosite and sum(sol_vars[grupo] for grupo in list(grupo_solucoes.loc['TWIN_BEAM','Solucao'])) <= 0
                    check_sol = True
                    for banda in list(set(df_solucoes['Banda'])):
                        for portadora in ['P1','P2','P3']:
                            for s in [0,1,2,3]:
                                check_sol = check_sol and modulo3_funcoes.sol_excludentes(df_solucoes, sol_vars, banda, portadora, s) <= 1
                    if (check_biosite and check_sol == True):
                        var_status = "Repescagem"
                
                ## Alimentar df de resultado: df_pulp
                df_pulp = df_pulp.append({'End_id':endid,
                                        'Status': var_status, #Indica o status da solução do problema
                                        'S1_CapTarget': S1_Target,
                                        'S2_CapTarget': S2_Target,
                                        'S3_CapTarget': S3_Target,
                                        #'S1_CapTarget_Tolerancia': prob.variables()[0].varValue,                               
                                        'S1_Penalidade': prob.variables()[2].varValue,
                                        #'S2_CapTarget_Tolerancia': prob.variables()[3].varValue,
                                        'S2_Penalidade': prob.variables()[5].varValue,
                                        #'S3_CapTarget_Tolerancia': prob.variables()[6].varValue,
                                        'S3_Penalidade': prob.variables()[8].varValue,                  
                                        'Solucoes': solucao_pulp,
                                        'Custo Considerado': round(value(prob.objective),2)},
                                        ignore_index = True)
            else:
                df_pulp = df_pulp.append({'End_id':endid,
                                            'Status': "NSA",
                                            'Solucoes': "Não há soluções disponíveis"},
                                            ignore_index = True)


        else:
            df_pulp = df_pulp.append({'End_id':endid,
                                        'Status': "NSA",
                                        'Solucoes': "Site MOCN - Tim Tomadora"},
                                        ignore_index = True) 
 

    ## Export Pulp
    df_pulp['Custo Considerado'] = df_pulp['Custo Considerado'] - ((df_pulp['S1_Penalidade']+df_pulp['S2_Penalidade']+df_pulp['S3_Penalidade'])*config.__PENALIDADE)

    conditions  = [(df_pulp['S1_Penalidade'] == 0) & (df_pulp['S2_Penalidade'] == 0) & (df_pulp['S3_Penalidade'] == 0)]
    choices     = ['OK']
    df_pulp['Flag'] = np.select(conditions, choices, default='Provisório')

    conditions  = [(df_pulp['Custo Considerado'] == 0.0) & (df_pulp['Status'] == 'Optimal'), ((df_pulp['Custo Considerado'] == 0.0) & (df_pulp['Status'] == 'Repescagem')) | (df_pulp['Status'] == 'NSA') | (df_pulp['Status'] == 'Infeasible')]
    choices     = ['Op Balanceamento', 'NOK']
    df_pulp['Flag'] = np.select(conditions, choices, default = df_pulp['Flag'])

    arq_saida = config.__ARQUIVO_SOLUCOES_PULP + datetime.datetime.now().strftime("%d_%m_%y-%H_%M_%S") + ".xlsx"
    df_pulp.to_excel(arq_saida, index = False)
    config.PrintComHora('Modulo 3... Concluido!')


if __name__ == '__main__':
    main()
    config.PrintComHora('Modulo 3...Concluido!')

