import pickle

import pandas as pd
from database.redis_connection import r
from config import settings

def authorize_by_file(user_id:str, user_role:str, df: pd.DataFrame, row_rules:dict):
    print("The user role is ", user_role)
    print("The user id is ", user_id)
    row_rules = row_rules.get('rowRules', {})
    roles = row_rules.keys()
    print("The row rules are ", row_rules)
    if user_id != 'duythai':
        for role in roles:
            print("The role of current is ", role)
            if role == user_role:
                print('This go inside ')
                print("we have ", row_rules[role])
                for permission in row_rules[role]:
                    print(permission, permission["column"])
                    df = df[df[permission["column"]] == int(user_id)]
                    print("we run into this read along column")
    return df

def authorize_by_db(user_id:str, user_role:str, df: pd.DataFrame, row_rules:dict):
    # Get user_role from database by user_id
    print("The user role is ", user_role)
    if user_role.lower() in settings.OPC_AUTH_ADMIN:
        return df
    elif user_role.upper() == "BM":
        # go to database to get the list of user_ids that this BM can see
        bm_df = r.get(settings.OPC_DB_GSBH_CACHE_NAME)
        if bm_df is not None:
            bm_df = pickle.loads(bm_df)
            list_user_under_id = bm_df[bm_df['NHANVIEN_FK'].astype(str).str.replace(r'\.0$', '', regex=True) == user_id]['GSSBH_FK'].tolist()
            # print("The list of user under this BM is ", list_user_under_id)
            # print("----------- debug ------------------")
            # print("The user id is ", user_id)
            # print("The BM dataframe is ", bm_df)
            # print("Check if the user id is in the BM dataframe")
            # print(bm_df["NHANVIEN_FK"].astype(str).str.replace(r'\.0$', '', regex=True) == user_id)
            # print("The GSSBHFK in the BM dataframe is ", bm_df['GSSBH_FK'])


            df = df[df['GSBH_FK'].isin(list_user_under_id)]
        return df
    elif user_role.upper() == "DDKD":
        df = df[df['DDKD_FK'].astype(str).str.replace(r'\.0$', '', regex=True) == user_id]
        return df
    elif user_role.upper() == "GSBH":
        df = df[df['GSBH_FK'].astype(str).str.replace(r'\.0$', '', regex=True) == user_id]
        return df
    else:
        return df


def authorize(row_rules:dict, user_id:str, user_role:str, df: pd.DataFrame, selected_db):
    if len(row_rules) == 0:
        return authorize_by_db(user_id, user_role, df, row_rules)
    else:
        print("The database is ", selected_db.split("_")[0])
        print("The authorization require db is ", settings.AUTHORIZATION_REQUIRE_DB)
        return authorize_by_file(user_id, user_role, df, row_rules)


