from learners.learner import RobustLearner
from data_reader.input import Instance, FeatureVector
from adversaries.adversary import Adversary
from typing import List, Dict
import numpy as np
import cvxpy as cvx

OPT_INSTALLED = True
try:
    import cvxopt
except ImportError:
    OPT_INSTALLED = False



class SVM_Restrained(RobustLearner):
    """Solves asymmetric dual problem: :math:`argmin (1/2)*⎜⎜w⎟⎟^2 + C*∑(xi0)`

    By solving the convex optimization, optimal weight and bias matrices are
    computed to be used in the linear classification of the instances
    changed by the adversary.

    Args:
        c_delta: aggressiveness assumption c_delta ∈ [0.0,1.0]. Default:0.5
    """

    def __init__(self, params = None, training_instances = None):
        RobustLearner.__init__(self)
        self.weight_vector = None
        self.bias = 0
        if params is not None:
            self.set_params(params)
        if training_instances is not None:
            self.set_training_instances(training_instances)


    def set_params(self, params: Dict):
        # TODO: set params needed
        raise NotImplementedError

    def train(self):
        self.c = 10
        # self.atk_f = 0.5 # this parameter can be tweaked
        #TODO: add this to __init__:
        num_instances = len(self.training_instances)
        Xn_list = [ins.feature_vector for ins in self.training_instances if ins.get_label()== InitialPredictor.negative_classification]
        Xp_list = [ins.feature_vector for ins in self.training_instances if ins.get_label()== InitialPredictor.positive_classification]
        y_list = [ins.label for ins in self.training_instances]
        self.c_delta = 0.5 # this parameter can be tweaked
        self.neg_i = np.array([i.get_feature_values() for i in Xn_list])
        self.pos_i = np.array([i.get_feature_values() for i in Xp_list])
        
        # centroid can be computed in multiple ways (might need to specify axis = 0)
        self.n_centroid = np.mean(self.neg_i)
        Mk_ = ((1- self.c_delta * np.fabs(self.n_centroid - self.pos_i)/
              (np.fabs(self.n_centroid)+np.fabs(self.pos_i)))*
              ((self.n_centroid-self.pos_i)**2))
        Zks = np.zeros_like(self.neg_i)
        self.Mk = np.stack((Mk_,Zks))
        self.TMk = np.stack((self.n_centroid - self.pos_i,Zks))
        self.ones_col = np.ones((self.neg_i.shape[1],1))
        self.pn = np.stack((self.pos_i,self.neg_i))
        self.pl = np.ones((self.pos_i[0],1))
        self.nl = -np.ones((self.neg_i[0],1))
        self.pnl = np.stack((self.pl,self.nl))
        #self.set_adversarial_params()

        col_neg, row_sum = self.neg_i.size[1], self.pos_i.size[0] + self.neg_i.size[0]

        w = cvx.Variable(col_neg)
        b = cvx.Variable()
        xi0 = cvx.Variable(row_sum)
        t = cvx.Variable(row_sum)
        u = cvx.Variable(row_sum,col_neg)
        v = cvx.Variable(row_sum,col_neg)

        constraints = [xi0>=0,
                       xi0 >=1-self.pnl*(np.dot(self.pn,w)+b)+t,
                       t>=np.dot((u*self.Mk),self.ones_col),
                       (-u+v)*self.TMk==0.5*np.tile((1+self.pnl),(1,col_neg))*np.tile(w.T,(row_sum,1)),
                       u>=0,
                       v>=0]
        # Objective
        # TODO: Test to see if this should be cvx.sum()
        obj = cvx.Minimize(0.5*(cvx.norm(w)) + self.c*cvx.sum_entries(xi0))
        prob = cvx.Problem(obj,constraints)
        if OPT_INSTALLED:
            prob.solve(solver='CVXOPT')
        else:
            prob.solve()

        self.weight_vector = w.value
        self.bias = b.value


        # def cvx_optimize(self, col_neg: int, row_sum: int):
        #     """Optimize the asymmetric dual problem and return optimal w and b.
        #
        #     Args:
        #         col_neg: int number of columns of negative instances
        #         row_sum: int sum of rows of negative and positive instances
        #     """
        #
        #     w = cvx.Variable(col_neg)
        #     b = cvx.Variable()
        #     xi0 = cvx.Variable(row_sum)
        #     t = cvx.Variable(row_sum)
        #     u = cvx.Variable(row_sum,col_neg)
        #     v = cvx.Variable(row_sum,col_neg)
        #
        #     constraints = [xi0>=0,
        #                    xi0 >=1-self.pnl*(np.dot(self.pn,w)+b)+t,
        #                    t>=np.dot((u*self.Mk),self.ones_col),
        #                    (-u+v)*self.TMk==0.5*np.tile((1+self.pnl),(1,col_neg))*np.tile(w.T,(row_sum,1)),
        #                    u>=0,
        #                    v>=0]
        #     # Objective
        #     # TODO: Test to see if this should be cvx.sum()
        #     obj = cvx.Minimize(0.5*(cvx.norm(w)) + self.c*cvx.sum_entries(xi0))
        #     prob = cvx.Problem(obj,constraints)
        #     if OPT_INSTALLED:
        #         prob.solve(solver='CVXOPT')
        #     else:
        #         prob.solve()
        #     return {'weight':w.value,'bias':b.value}



    def predict(self, instances: List[Instance]):
        predictions = []
        for instance in instances:
            features = instance.get_feature_vector().get_csr_matrix().toarray()[0]
            predictions.append(np.sign(self.predict_instance(features)))
        return predictions

    def predict_instance(self, features: FeatureVector):
        return np.dot(features, self.weight_vector) + self.bias

    def predict_proba(self, instances: List[Instance]):
        return [self.predict_instance(
            ins.get_feature_vector().get_csr_matrix().toarray()[0]) for ins in instances]
