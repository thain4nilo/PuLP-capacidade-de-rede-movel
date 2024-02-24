# 📡 Solução de Capacidade para Rede Móvel

Este projeto visa resolver problemas de implantação de capacidade para Estações Rádio Base (ERB) utilizando a biblioteca PuLP do Python, que é uma ferramenta para modelagem de problemas de Programação Linear (LP). Neste projeto, exploramos as técnicas de pesquisa operacional para determinar o conjunto ideal de soluções que permitam atingir uma capacidade alvo em uma Estação Rádio Base.

## Bibliotecas utilizadas
```
from pulp import *
import pandas as pd
import numpy as np
import config
import datetime
import warnings
from tqdm import tqdm
```
## Inputs
- Planilha de levantamento do estado atual da rede: soluções já disponíveis no end_id
- Planilha de custos x capacidade da solução: capacidade, custo para cada solução e grupo/categoria na qual esta pertence (LAYER, mMIMO)
- Planilha de restrições: soluções possíveis de serem implantadas por end_id, levando em consideração: biosite, banda p, refarming
- Planilha de capacidade necessária: PRB necessário para colocar end_id na meta
## Outputs:
- Planilha com endereço Id e solução sugerida indicando também eventuais penalizações para alcançar o target de PRB
