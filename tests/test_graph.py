import networkx as nx
from railway_graph import create_railway_network

def test_create_railway_network():
    G = create_railway_network()
    assert isinstance(G, nx.Graph)
    assert G.has_node("Howrah (HWH)")
    assert G.has_edge("Howrah (HWH)", "Bandel (BDC)")
    
    # Test path exists initially
    assert nx.has_path(G, "Howrah (HWH)", "Bardhaman (BWN)")
    
    # Test removing an edge removes path
    G.remove_edge("Howrah (HWH)", "Bandel (BDC)")
    has_path = nx.has_path(G, "Howrah (HWH)", "Bardhaman (BWN)")
    assert not has_path
