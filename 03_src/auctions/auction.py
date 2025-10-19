import numpy as np

import random
import re

from multiprocessing import Lock, Pool, Manager


############################################
# Buyer implementation:
class Buyer:
    def __init__(self, buyer_id, distances, pv=1000, beta=0.5, pvmax=1000):
        self.id = buyer_id
        self.state = "overbid"
        self.pv = pv
        self.beta = beta
        self.pvmax = pvmax
        self.distances = distances
        self.prices = {}
        
    def inform_price(self, auction_id, price):
        self.prices[auction_id] = price if price <= self.pv else np.inf
        if np.all(np.array(self.prices) == np.inf):
            self.state = "out_of_budget"
        
    def compute_costs(self):
        prices, distances, id_list = [], [], []
        for p in self.prices:
            prices.append(self.prices[p])
            pname = re.sub("_[0-9]*$", "", p)
            if "garage" in pname:
                edge = pname.split("_")[1]
            else:
                edge = pname.split("pa")[-1]
            distances.append(self.distances[edge])
            id_list.append(p)
        prices = np.array(prices)
        distances = np.array(distances)
        cost = self.beta*prices/self.pvmax + (1-self.beta)*distances/np.max(distances)
        return cost, id_list
        
    def ask_bid(self, auction_id, price):
        bids = False
        pref_ids = []
        if (self.state == "overbid") and (price <= self.pv):
            costs, ids = self.compute_costs()
            prefs = np.where(costs == costs.min())[0]
            for p in prefs:
                pref_ids.append(ids[p])
            bids = auction_id in pref_ids
        #if self.id == "carIn967:4":
        #        print(bids, pref_ids, auction_id)
        elif price > self.pv:
            self.prices[auction_id] = np.inf
        if bids:
            self.state = "winning"
        return bids
    
    def tell_overbid(self):
        self.state = "overbid"
        
    def tell_won(self):
        self.state = "won"
    
#############################################
# Auctioneer implementation:
class Auction:
    def __init__(self, id_, starting_price, epsilon=1.0):
        self.id = id_
        self.price = starting_price
        self.buyers = []
        self.epsilon = epsilon
        self.winner = None
        
    def add_buyer(self, buyer):
        self.buyers.append(buyer)
        
    def _inform_buyers(self):
        for b in self.buyers:
            b.inform_price(self.id, self.price)
        
    def auction_round(self):
        bid_received = False
        for b in self.buyers:                
            bids = b.ask_bid(self.id, self.price)
            if bids:
                if self.winner is not None:
                    self.winner.tell_overbid()
                self.winner = b
                self.price += self.epsilon
                self._inform_buyers()
                bid_received = True
        return bid_received
                
    def terminate(self):
        winner_id = ""
        if self.winner is not None:
            self.winner.tell_won()
            winner_id = self.winner.id
        return {"winner": winner_id,
                "price" : self.price-self.epsilon}
                
                
#############################################
# Running auctions:

def check_terminable(buyers):
    non_terminated_buyers = 0
    for b in buyers:
        if not((b.state == "winning") or (b.state == "out_of_budget")):
            non_terminated_buyers += 1
    return len(buyers) - non_terminated_buyers
    
    
def run_auctions(auctions, buyers, r_max):
    auction_results = {}
    rs = np.zeros(len(auctions))
    
    terminables = 0

    while (terminables != len(buyers)): # np.sum(rs<r_max) :
        #print(f"auction round: {terminables}/{len(buyers)}")
        i = 0
        while (len(buyers) != terminables) and (i<len(auctions)):
            bid_received = auctions[i].auction_round()
            if bid_received:
                rs[i] = 0
            else:
                rs[i] += 1

            terminables = check_terminable(buyers)
            i += 1
                
    for a in auctions:
        auction_results[a.id] = a.terminate()  
    return auction_results


def get_won_auctions(auction_results, buyers):
    won_auctions = {}
    for b in buyers:
        for a in auction_results:
            if auction_results[a]["winner"] == b.id:
                won_auctions[b.id] = a
    return won_auctions

def init_auction_method(parking_capacities, vehicle_ids, starting_prices, parking_mtx, betas=None, bid_step = 0.05, max_price = 5)-> (list, list):
    """Initializes the participants of the auction method
       -------------
       parameters:
           - parking_capacities: capacity values of the parking lots (number of auctions),
           - vehicle_ids: IDs of vehicles (buyers),
           - starting_prices: dict of starting prices of the auctions,
           - parking_mtx: mtx of parking distances for each vehicle
           - betas: either a dict of vehicle_ids, betas, a float, or None. Default: 0.1
           - bid_step: amount of money by which current bids will be increased during auctions,
           - max_price: maximum price that the buyers are willing to accept"""
    
    auctions = []
    buyers = []
    if betas is None:
        betas = 0.1
    if type(betas) is float:
        betas_ = {}
        for b_i in vehicle_ids:
            betas_[b_i] = betas
    else:
        betas_ = betas
            
    for i, b_i in enumerate(vehicle_ids):
        buyers.append(Buyer(b_i, parking_mtx[b_i], beta = betas_[b_i], pv=max_price, pvmax=max_price))
    for a in parking_capacities:
        for i in range(parking_capacities[a]):
            auctions.append(Auction(f"{a}_{i}", starting_prices[a], bid_step))
    random.shuffle(auctions)
    for a in auctions:
        for b in buyers:
            a.add_buyer(b)
            b.inform_price(a.id, a.price)
            
    return auctions, buyers