import numpy as np #minenotater til galerkin
import sympy as sp
import scipy.sparse as sparse
from scipy.integrate import quad
from numpy.polynomial import Legendre as Leg
from numpy.polynomial import Chebyshev as Cheb

x = sp.Symbol('x')

#mapper referansedomenet, som vel er mellom -1 og 1?
def map_reference_domain(x, d, r):
    return r[0] + (r[1]-r[0])*(x-d[0])/(d[1]-d[0])

#mapper det ekte domenet. 
def map_true_domain(x, d, r):
    return d[0] + (d[1]-d[0])*(x-r[0])/(r[1]-r[0])

#sympify lager om til et sympytall
def map_expression_true_domain(u, x, d, r):
    if d != r:
        u = sp.sympify(u)
        xm = map_true_domain(x, d, r)
        u = u.replace(x, xm)
    return u

"""---------------------------------FUNCTION SPACE-----------------------------------"""
class FunctionSpace:
    def __init__(self, N, domain=(-1, 1)):
        self.N = N
        self._domain = domain

    @property
    def domain(self):
        return self._domain

    @property
    def reference_domain(self):
        raise RuntimeError 

    @property
    def domain_factor(self):
        d = self.domain
        r = self.reference_domain
        return (d[1]-d[0])/(r[1]-r[0])

    def mesh(self, N=None):
        d = self.domain
        n = N if N is not None else self.N
        return np.linspace(d[0], d[1], n+1)

    def weight(self, x=x):
        return 1

    def basis_function(self, j, sympy=False):
        raise RuntimeError 

    def derivative_basis_function(self, j, k=1):
        raise RuntimeError 

    def evaluate_basis_function(self, Xj, j):
        return self.basis_function(j)(Xj)

    def evaluate_derivative_basis_function(self, Xj, j, k=1):
        return self.derivative_basis_function(j, k=k)(Xj)

    def eval(self, uh, xj):
        xj = np.atleast_1d(xj)
        Xj = map_reference_domain(xj, self.domain, self.reference_domain)
        P = self.eval_basis_function_all(Xj)
        return P @ uh

    def eval_basis_function_all(self, Xj):
        P = np.zeros((len(Xj), self.N+1))
        for j in range(self.N+1):
            P[:, j] = self.evaluate_basis_function(Xj, j)
        return P

    def eval_derivative_basis_function_all(self, Xj, k=1):
        P = np.zeros((len(Xj), self.N + 1))
        for j in range(self.N + 1):
            P[:, j] = self.evaluate_derivative_basis_function(Xj, j, k=1)
        return P
        #raise NotImplementedError #må implementeres

    def inner_product(self, u):
        us = map_expression_true_domain(
            u, x, self.domain, self.reference_domain)
        us = sp.lambdify(x, us)
        uj = np.zeros(self.N+1)
        h = self.domain_factor
        r = self.reference_domain
        for i in range(self.N+1):
            psi = self.basis_function(i)
            def uv(Xj): return us(Xj) * psi(Xj)
            uj[i] = float(h) * quad(uv, float(r[0]), float(r[1]))[0]
        return uj

    def mass_matrix(self):
        return assemble_generic_matrix(TrialFunction(self), TestFunction(self))

"""---------------------------------LEGENDRE POLYNOMIALS-----------------------------------"""
class Legendre(FunctionSpace):

    def __init__(self, N, domain=(-1, 1)):
        FunctionSpace.__init__(self, N, domain=domain)

    @property
    def reference_domain(self):
        return (-1, 1)

    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.legendre(j, x)
        return Leg.basis(j)

    def derivative_basis_function(self, j, k=1):
        return self.basis_function(j).deriv(k)

    def L2_norm_sq(self, N):
        #her hadde filmon noe
        L2_norms_sq = np.zeros(N+1)
        for i in range(N+1):
            L2_norms_sq[i] = 2/(2*i+1)
        return L2_norms_sq
        #raise NotImplementedError #må implementeres

    def mass_matrix(self):
        L2_norms_sq = self.L2_norm_sq(self.N) #simon n+1?
        A = sparse.diags([L2_norms_sq], [0], (self.N+1, self.N+1), format='csr')
        return A
        #raise NotImplementedError #må implementeres. den er diagonal. se lecture 8. kan lages dense. eller scipy sparse.

    def eval(self, uh, xj):
        xj = np.atleast_1d(xj)
        Xj = map_reference_domain(xj, self.domain, self.reference_domain)
        return np.polynomial.legendre.legval(Xj, uh)

"""---------------------------------CHEBYSHEV-----------------------------------"""
class Chebyshev(FunctionSpace):
    def __init__(self, N, domain=(-1, 1)):
        FunctionSpace.__init__(self, N, domain=domain)
    
    @property
    def reference_domain(self):
        return (-1, 1)
    
    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.cos(j*sp.acos(x))
        return Cheb.basis(j)

    def derivative_basis_function(self, j, k=1):
        return self.basis_function(j).deriv(k)

    def weight(self, x=x):
        return 1/sp.sqrt(1-x**2)

    def L2_norm_sq(self, N):
        r = self.reference_domain
        L2 = np.zeros(N + 1)
        L2 = np.ones(N + 1) * np.pi / 2
        L2[0] *= 2
        return L2
        #raise NotImplementedError #må implementeres

    def mass_matrix(self):
        L2_norms = self.L2_norm_sq(self.N)
        A = sparse.diags([L2_norms], [0], (self.N+1, self.N+1), format='csr')
        return A
        #raise NotImplementedError #må implementeres

    def eval(self, uh, xj):
        xj = np.atleast_1d(xj)
        Xj = map_reference_domain(xj, self.domain, self.reference_domain)
        return np.polynomial.chebyshev.chebval(Xj, uh)

    def inner_product(self, u):
        us = map_expression_true_domain(
            u, x, self.domain, self.reference_domain)
        # change of variables to x=cos(theta)
        us = sp.simplify(us.subs(x, sp.cos(x)), inverse=True)
        us = sp.lambdify(x, us)
        uj = np.zeros(self.N+1)
        h = float(self.domain_factor)
        k = sp.Symbol('k')
        basis = sp.lambdify((k, x), sp.simplify(
            self.basis_function(k, True).subs(x, sp.cos(x), inverse=True)))
        for i in range(self.N+1):
            def uv(Xj, j): return us(Xj) * basis(j, Xj)
            uj[i] = float(h) * quad(uv, 0, np.pi, args=(i,))[0]
        return uj

class Trigonometric(FunctionSpace):
    """Base class for trigonometric function spaces"""

    @property
    def reference_domain(self):
        return (0, 1)

    def mass_matrix(self):
        return sparse.diags([self.L2_norm_sq(self.N+1)], [0], (self.N+1, self.N+1), format='csr')

    def eval(self, uh, xj):
        xj = np.atleast_1d(xj)
        Xj = map_reference_domain(xj, self.domain, self.reference_domain)
        P = self.eval_basis_function_all(Xj)
        return P @ uh + self.B.Xl(Xj)

"""---------------------------------SIN-----------------------------------"""
class Sines(Trigonometric):

    def __init__(self, N, domain=(0, 1), bc=(0, 0)):
        Trigonometric.__init__(self, N, domain=domain)
        self.B = Dirichlet(bc, domain, self.reference_domain)

    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.sin((j+1)*sp.pi*x)
        return lambda Xj: np.sin((j+1)*np.pi*Xj)

    def derivative_basis_function(self, j, k=1):
        scale = ((j + 1) * np.pi) ** k * {0: 1, 1: 1, 2: -1, 3: -1}[k % 4]
        #scale = ((j+1)*np.pi)**k * {0: 1, 1: -1}[(k//2) % 2]
        if k % 2 == 0:
            return lambda Xj: scale*np.sin((j+1)*np.pi*Xj)
        else:
            return lambda Xj: scale*np.cos((j+1)*np.pi*Xj)

    def L2_norm_sq(self, N):
        return 0.5 * np.ones(N+1)

"""---------------------------------COS-----------------------------------"""
class Cosines(Trigonometric):

    def __init__(self, N, domain=(0, 1), bc=(0, 0)):
        Trigonometric.__init__(self, N, domain=domain)
        self.B = Neumann(bc, domain, self.reference_domain)
        #raise NotImplementedError

    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.cos(j*sp.pi*x)# byttet sin med cos, fjernet +1
        return lambda Xj: np.cos(j*np.pi*Xj) #byttet sin med cos
        #raise NotImplementedError

    def derivative_basis_function(self, j, k=1):
        scale = (j*np.pi)**k * {0: 1, 1: -1, 2:-1, 3:1}[k % 4]
        if k % 2 == 0:
            return lambda Xj: scale*np.cos(j*np.pi*Xj) #bytta sin med cos
        else:
            return lambda Xj: scale*np.sin(j*np.pi*Xj) #bytta cos med sin
        # raise NotImplementedError

    def L2_norm_sq(self, N):
        L2 = 0.5*np.ones(N+1)
        L2[0] = 1
        return L2
       # raise NotImplementedError #må implementeres

# Create classes to hold the boundary function
"""---------------------------------DIRICHLET-----------------------------------"""
class Dirichlet:

    def __init__(self, bc, domain, reference_domain):
        d = domain
        r = reference_domain
        h = d[1]-d[0]
        self.bc = bc
        self.x = bc[0]*(d[1]-x)/h + bc[1]*(x-d[0])/h           # in physical coordinates
        self.xX = map_expression_true_domain(self.x, x, d, r)  # in reference coordinates
        self.Xl = sp.lambdify(x, self.xX)

"""---------------------------------NEUMANN-----------------------------------"""
class Neumann:

    def __init__(self, bc, domain, reference_domain):
        d = domain
        r = reference_domain
        h = d[1]-d[0]
        self.bc = bc
        self.x = bc[0]/h*(d[1]*x-x**2/2) + bc[1]/h*(x**2/2-d[0]*x)  # in physical coordinates
        self.xX = map_expression_true_domain(self.x, x, d, r)       # in reference coordinates
        self.Xl = sp.lambdify(x, self.xX)


class Composite(FunctionSpace):
    def eval(self, uh, xj):
        xj = np.atleast_1d(xj)
        Xj = map_reference_domain(xj, self.domain, self.reference_domain)
        P = self.eval_basis_function_all(Xj)
        return P @ uh + self.B.Xl(Xj)

    def mass_matrix(self):
        M = sparse.diags([self.L2_norm_sq(self.N+3)], [0],
                         shape=(self.N+3, self.N+3), format='csr')
        return self.S @ M @ self.S.T


class DirichletLegendre(Composite, Legendre):
    def __init__(self, N, domain=(-1, 1), bc=(0, 0)):
        Legendre.__init__(self, N, domain=domain)
        self.B = Dirichlet(bc, domain, self.reference_domain)
        self.S = sparse.diags((1, -1), (0, 2), shape=(N+1, N+3), format='csr')

    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.legendre(j,x)- sp.legendre(j+2,x)
        return Leg.basis(j)-Leg.basis(j+2)
        #raise NotImplementedError #må implementeres


class NeumannLegendre(Composite, Legendre):
    def __init__(self, N, domain=(-1, 1), bc=(0, 0), constraint=0):
        Legendre.__init__(self,N,domain=domain)
        self.B = Neumann(bc, domain, self.reference_domain)
        self.S = sparse.diags((1,-1),(0,2), shape=(N+1, N+3), format='csr')
        for i in range(N + 1):
            self.S[i, i + 2] = -i * (i + 1) / ((i + 2) * (i + 3))
        #raise NotImplementedError #må implementeres

    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.legendre(j,x) - sp.legendre(j+2,x)*j(j+1)/((j+2)*(j+3))
        return Leg.basis(j)-Leg.basis(j+2)*j*(j+1)/((j+2)*(j+3))
        #raise NotImplementedError #må implementeres


class DirichletChebyshev(Composite, Chebyshev):

    def __init__(self, N, domain=(-1, 1), bc=(0, 0)):
        Chebyshev.__init__(self, N, domain=domain)
        self.B = Dirichlet(bc, domain, self.reference_domain)
        self.S = sparse.diags((1, -1), (0, 2), shape=(N+1, N+3), format='csr')

    def basis_function(self, j, sympy=False):
        if sympy:
            return sp.cos(j*sp.acos(x)) - sp.cos((j+2)*sp.acos(x))
        return Cheb.basis(j)-Cheb.basis(j+2)


class NeumannChebyshev(Composite, Chebyshev):
    def __init__(self, N, domain=(-1, 1), bc=(0, 0), constraint=0):
        Chebyshev.__init__(self, N, domain=domain)
        self.B = Neumann(bc, domain, self.reference_domain)
        self.S = sparse.diags((1, -1), (0, 2), shape=(N+1, N+3), format='csr')
        for i in range(N+1):
            self.S[i, i+2] = -((i / (i+2))**2)
        #raise NotImplementedError #må implementeres

    def basis_function(self, j, sympy=False):
        if sympy:
            return(sp.cos(j*sp.acos(x))-sp.cos((j+2)*sp.acos(x))* (j/(j+2))**2)
        return Cheb.basis(j) - Cheb.basis(j+2) * (j/(j+2))**2
        #raise NotImplementedError #må implementeres


class BasisFunction:

    def __init__(self, V, diff=0, argument=0):
        self._V = V
        self._num_derivatives = diff
        self._argument = argument

    @property
    def argument(self):
        return self._argument

    @property
    def function_space(self):
        return self._V

    @property
    def num_derivatives(self):
        return self._num_derivatives

    def diff(self, k):
        return self.__class__(self.function_space, diff=self.num_derivatives+k)


class TestFunction(BasisFunction):

    def __init__(self, V, diff=0):
        BasisFunction.__init__(self, V, diff=diff, argument=0)


class TrialFunction(BasisFunction):

    def __init__(self, V, diff=0):
        BasisFunction.__init__(self, V, diff=diff, argument=1)


def assemble_generic_matrix(u, v):
    assert isinstance(u, TrialFunction)
    assert isinstance(v, TestFunction)
    V = v.function_space
    assert u.function_space == V
    r = V.reference_domain
    D = np.zeros((V.N+1, V.N+1))
    cheb = V.weight() == 1/sp.sqrt(1-x**2)
    symmetric = True if u.num_derivatives == v.num_derivatives else False
    w = {'weight': 'alg' if cheb else None,
         'wvar': (-0.5, -0.5) if cheb else None}
    def uv(Xj, i, j): return (V.evaluate_derivative_basis_function(Xj, i, k=v.num_derivatives) *
                              V.evaluate_derivative_basis_function(Xj, j, k=u.num_derivatives))
    for i in range(V.N+1):
        for j in range(i if symmetric else 0, V.N+1):
            D[i, j] = quad(uv, float(r[0]), float(r[1]), args=(i, j), **w)[0]
            if symmetric:
                D[j, i] = D[i, j]
    return D


def inner(u, v: TestFunction):
    V = v.function_space
    h = V.domain_factor
    if isinstance(u, TrialFunction):
        num_derivatives = u.num_derivatives + v.num_derivatives
        if num_derivatives == 0:
            return float(h) * V.mass_matrix()
        else:
            return float(h)**(1-num_derivatives) * assemble_generic_matrix(u, v)
    return V.inner_product(u)


def project(ue, V):
    u = TrialFunction(V)
    v = TestFunction(V)
    b = inner(ue, v)
    A = inner(u, v)
    uh = sparse.linalg.spsolve(A, b)
    return uh


def L2_error(uh, ue, V, kind='norm'):
    d = V.domain
    uej = sp.lambdify(x, ue)
    def uv(xj): return (uej(xj)-V.eval(uh, xj))**2
    return np.sqrt(quad(uv, float(d[0]), float(d[1]))[0])


def test_project():
    ue = sp.besselj(0, x)
    domain = (0, 10)
    for space in (Chebyshev, Legendre):
        V = space(16, domain=domain)
        u = project(ue, V)
        err = L2_error(u, ue, V)
        print(
            f'test_project: L2 error = {err:2.4e}, N = {V.N}, {V.__class__.__name__}')
        assert err < 1e-6


def test_helmholtz():
    ue = sp.besselj(0, x)
    f = ue.diff(x, 2)+ue
    domain = (0, 10)
    for space in (NeumannChebyshev, NeumannLegendre, DirichletChebyshev, DirichletLegendre, Sines, Cosines):
        if space in (NeumannChebyshev, NeumannLegendre, Cosines):
            bc = ue.diff(x, 1).subs(x, domain[0]), ue.diff(
                x, 1).subs(x, domain[1])
        else:
            bc = ue.subs(x, domain[0]), ue.subs(x, domain[1])
        N = 60 if space in (Sines, Cosines) else 12
        V = space(N, domain=domain, bc=bc)
        u = TrialFunction(V)
        v = TestFunction(V)
        A = inner(u.diff(2), v) + inner(u, v)
        b = inner(f-(V.B.x.diff(x, 2)+V.B.x), v)
        u_tilde = np.linalg.solve(A, b)
        err = L2_error(u_tilde, ue, V)
        print(
            f'test_helmholtz: L2 error = {err:2.4e}, N = {N}, {V.__class__.__name__}')
        assert err < 1e-3


def test_convection_diffusion():
    eps = 0.05
    ue = (sp.exp(-x/eps)-1)/(sp.exp(-1/eps)-1)
    f = 0
    domain = (0, 1)
    for space in (DirichletLegendre, DirichletChebyshev, Sines):
        N = 50 if space is Sines else 16
        V = space(N, domain=domain, bc=(0, 1))
        u = TrialFunction(V)
        v = TestFunction(V)
        A = inner(u.diff(2), v) + (1/eps)*inner(u.diff(1), v)
        b = inner(f-((1/eps)*V.B.x.diff(x, 1)), v)
        u_tilde = np.linalg.solve(A, b)
        err = L2_error(u_tilde, ue, V)
        print(
            f'test_convection_diffusion: L2 error = {err:2.4e}, N = {N}, {V.__class__.__name__}')
        assert err < 1e-3
 


if __name__ == '__main__':
    test_project()
    test_convection_diffusion()
    test_helmholtz()
