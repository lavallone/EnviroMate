from unified_planning.shortcuts import *

problem = Problem("MatchCellar")
Match = UserType("Match")
Fuse = UserType("Fuse")


light = problem.add_fluent("light", BoolType(), default_initial_value=False)
# since BoolType is the default, it can be avoided
handfree = problem.add_fluent("handfree", default_initial_value=True)
match_used = problem.add_fluent("match_used", default_initial_value=False, m=Match)
fuse_mended = problem.add_fluent("fuse_mended", default_initial_value=False, f=Fuse)


light_match = DurativeAction("light_match", m=Match)
m = light_match.parameter("m")
light_match.set_fixed_duration(6)
light_match.add_condition(StartTiming(), Not(match_used(m)))
light_match.add_effect(StartTiming(), match_used(m), True)
light_match.add_effect(StartTiming(), light, True)
light_match.add_effect(EndTiming(), light, False)
problem.add_action(light_match)


mend_fuse = DurativeAction("mend_fuse", f=Fuse)
f = mend_fuse.parameter("f")
mend_fuse.set_fixed_duration(5)
mend_fuse.add_condition(StartTiming(), handfree)
mend_fuse.add_condition(ClosedTimeInterval(StartTiming(), EndTiming()), light)
mend_fuse.add_effect(StartTiming(), handfree, False)
mend_fuse.add_effect(EndTiming(), fuse_mended(f), True)
mend_fuse.add_effect(EndTiming(), handfree, True)
problem.add_action(mend_fuse)


obj_number = 3
match_objects = [Object(f"m{i}", Match) for i in range(1, obj_number + 1)]
problem.add_objects(match_objects)
fuse_objects = [Object(f"f{i}", Fuse) for i in range(1, obj_number + 1)]
problem.add_objects(fuse_objects)


for fuse_obj in fuse_objects:
    problem.add_goal(fuse_mended(fuse_obj))


from unified_planning.model.scheduling import SchedulingProblem

problem = SchedulingProblem("factory")
workers = problem.add_resource("workers", capacity=4)
machine1 = problem.add_resource("machine1", capacity=1)
machine2 = problem.add_resource("machine2", capacity=1)

a1 = problem.add_activity("a1", duration=3)
a1.uses(machine1)
a1.uses(workers, amount=2)
a1.add_deadline(14)

a2 = problem.add_activity("a2", duration=6)
a2.uses(workers)
a2.uses(machine2)

problem.add_constraint(LT(a2.end, a1.start))

# One worker is unavailable over [17, 25]
problem.add_decrease_effect(16, workers, 1)
problem.add_increase_effect(25, workers, 1)
