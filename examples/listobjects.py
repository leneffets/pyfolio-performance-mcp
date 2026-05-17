from pyfolio_performance import Portfolio, Security

port_perf = Portfolio("02_portfolio.xml")

print()
print("Accounts: #" + str(len(port_perf.get_accounts())))
for account in port_perf.get_accounts():
    print(account.get_name() + ": " + str(account.get_balance()))
print()

print("Transactions of #1 Account:")
acc = port_perf.get_accounts()[0]
for num, transaction in enumerate(acc.get_transactions()):
    print(
        "[" + str(transaction.date) + "] " + transaction.type + ": " + str(transaction.get_amount())
    )
    if num >= 4:
        break
print()

print("Depots: #" + str(len(port_perf.get_depots())))
for depot in port_perf.get_depots():
    print(depot.get_name())
print()

print("Transactions of #1 Depot:")
acc = port_perf.get_depots()[0]
for num, transaction in enumerate(acc.get_transactions()):
    print(
        "[" + str(transaction.date) + "] " + transaction.type + ": " + str(transaction.get_amount())
    )
    print("\t" + str(transaction.get_security()))
    if num >= 4:
        break
print()


# print("New purchases in ")
# def filter_month(entry, month, year):
#     if entry.get_year() != year or month != entry.get_month():
#         return False
#     return True
# print()

isin = "GB0007980591"  # BP PLC
print(f"Getting shares for ISIN {isin}")
sec = Security.get_security_by_isin(isin)
print(f"Got security: {sec}")
shares = port_perf.get_shares(sec)
print("Shares: " + str(shares))
print()

# print("Securities:")
# print({x.get_name(): x.get_logo()==None for x in portPerf.get_securities()})
# print()
