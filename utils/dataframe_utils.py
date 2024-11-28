import pandas as pd
import numpy as np
from pyparsing import Iterable

def pack_dataframe(data, ids : Iterable, labels : Iterable, time_points : Iterable):
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else: df = pd.DataFrame(data)

    df['ids'] = ids
    df['labels'] = labels
    df['time points'] = time_points
    return df


def unpack_dataframe(df) -> tuple[pd.DataFrame, np.array, np.array, np.array]:
    data = df.drop(['ids', 'labels', 'time points'], axis=1)
    return data, df['ids'], df['labels'], df['time points']


'''
To avoid altering the original list of dataframes to concat, a copy is made of the list. If the list is discartable, set skip_copy to true 
'''
def concact_dataframes(target_df : pd.DataFrame, concating_dfs : list[pd.DataFrame], skip_copy: bool = False) -> pd.DataFrame:
    if not skip_copy:
        data_copy = concating_dfs.copy()
    else:
        data_copy = concating_dfs
    data_copy.insert(0, target_df)
    return pd.concat(data_copy, ignore_index=True, axis=0)