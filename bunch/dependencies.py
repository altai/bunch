from exceptions import CyclicDependencySpecification
from topsort import topsort_levels,CycleError
from itertools import chain, tee, izip, product

def pairwise(iterable):
    a, b = tee(iterable)
    next(b)
    return izip(a, b)

def dependency_lists_to_pairs(dependency_lists):
    return chain(*(pairwise(dep_list) for dep_list in dependency_lists))

def dependency_groups_to_pairs(groups):
    return chain(*(product(a,b) for a,b in pairwise(groups)))

def split_solitaries(deps):
    solitaries = []
    linked = []
    for dep in deps:
        if len(dep) == 1 and len(dep[0]) == 1:
            solitaries.append(dep[0])
        else:
            linked.append(dep)
    return solitaries, linked


def combine_fixture_deps(deps):
    solitary, linked = split_solitaries(deps)
    try:
        result = [group for group in topsort_levels(chain(*map(dependency_groups_to_pairs, linked)))]
        result.extend(solitary)
    except CycleError as cycle_details:
        raise CyclicDependencySpecification(cycle_details)

    return result

