import pickle

# f = open('data_users.pkl', 'wb')
# pickle.dump(dict(row_user_id=[123, 456, 789], row_name=['dem', 'anny', 'jon'], row_count_query=[2, 4, 6],
#                  row_count_tokens=[23, 43, 65], row_query_limit=[2, 5, 9], last_enter=['2023-04-27', '2021-04-27',
#                                                                                        '2023-04-25']), f)
# f.close()

f = open('data_users.pkl', 'rb')
rr = pickle.load(f)
f.close()

print(rr)
