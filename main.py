from pyfolio_performance import Portfolio, Security

if __name__ == "__main__":
    port_perf = Portfolio("02_portfolio.xml")

    test_security = Security.get_security_by_name("BP")

    print(port_perf.get_shares(test_security))  # should be around 122

    # Testing the methods
    sec_by_isin = Security.get_security_by_isin("DE0005190003")
    if sec_by_isin is not None:
        print(sec_by_isin.get_most_recent_value())
    sec_by_wkn = Security.get_security_by_wkn("878841")
    if sec_by_wkn is not None:
        print(sec_by_wkn.name)

    print(port_perf.get_accounts())
    print(port_perf.get_depots())

    for sec in port_perf.get_securities():
        print(sec.get_name())
        print(sec.get_most_recent_value())
