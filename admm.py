import numpy as np
from numpy.linalg import inv
from numpy.linalg import norm
from joblib import Parallel, delayed
import multiprocessing

class ADMM:
    def __init__(self, A, b, parallel = False):
        self.D = A.shape[1]
        self.N = A.shape[0]
        if parallel:
            self.XBar = np.zeros((self.N, self.D))
            self.nuBar = np.zeros((self.N, self.D))
        self.nu = np.zeros((self.D, 1))
        self.rho = 1
        self.X = np.random.randn(self.D, 1)
        self.Z = np.zeros((self.D, 1))
        self.A = A
        self.b = b
        self.alpha = 0.01
        self.parallel = parallel
        self.numberOfThreads = multiprocessing.cpu_count()

    def step(self):
        if self.parallel:
            return self.step_parallel()

        # Solve for X_t+1
        self.X = inv(self.A.T.dot(self.A) + self.rho).dot(self.A.T.dot(self.b) + self.rho * self.Z - self.nu)
        
        # Solve for Z_t+1
        self.Z = self.X + self.nu / self.rho - (self.alpha / self.rho) *  np.sign(self.Z)
        # Combine
        self.nu = self.nu + self.rho * (self.X - self.Z)
    
    def solveIndividual(self, i):
        A = self.A[i]
        b = np.asscalar(self.b[i])
        nu = self.nuBar[i].reshape(-1, 1)
        t1 = A.dot(A.T)
        A = A.reshape(-1, 1)
        tX = (A * b + self.rho * self.Z - nu) / (t1 + self.rho)
        return tX

    def combineSolution(self, i):
        t = self.nuBar[i].reshape(-1, 1)
        t = t + self.rho * (self.XBar[i].reshape(-1, 1) - self.Z)
        self.nuBar[i] = t.T


    def step_parallel(self):
        # Solve for X_t+1
        Parallel(n_jobs = self.numberOfThreads, backend = "threading")(
            delayed(self.solveIndividual)(i) for i in range(0, self.N-1))
        
        self.X = np.average(self.XBar, axis = 0) 
        self.nu = np.average(self.nuBar, axis = 0)
        
        self.X = self.X.reshape(-1, 1)
        self.nu = self.nu.reshape(-1, 1)
        
        # Solve for Z_t+1
        self.Z = self.X + self.nu / self.rho - (self.alpha / self.rho) * np.sign(self.Z)
        # Combine
        Parallel(n_jobs = self.numberOfThreads, backend = "threading")(
            delayed(self.combineSolution)(i) for i in range(0, self.N-1))
        
    def step_iterative(self):
        # Solve for X_t+1
        for i in range(0, self.N-1):
            t = self.solveIndividual(i)
            self.XBar[i] = t.T
        
        self.X = np.average(self.XBar, axis = 0) 
        self.nu = np.average(self.nuBar, axis = 0)
        
        self.X = self.X.reshape(-1, 1)
        self.nu = self.nu.reshape(-1, 1)

        # Solve for Z_t+1
        self.Z = self.X + self.nu / self.rho - (self.alpha / self.rho) * np.sign(self.Z)

        # Combine
        for i in range(0, self.N-1):
            t = self.nuBar[i].reshape(-1, 1)
            t = t + self.rho * (self.XBar[i].reshape(-1, 1) - self.Z)
            self.nuBar[i] = t.T

    def LassoObjective(self):
        return 0.5 * norm(self.A.dot(self.X) - self.b)**2 + self.alpha *  norm(self.X, 1)
