# TODO choose a spelling (analyzed is American, analysed is British)


from collections import namedtuple


NONE = 0
UP = 1
DOWN = 2

# TODO: make .name a property of analysis
Analysis = namedtuple('Analysis', ['direction', 'dependencies', 'f'])

TimedOutput = namedtuple('TimedOutput', ['time', 'output'])


analysis_graph = {
    'analysis-1': Analysis(UP, ['source'], analysis_1),
    'analysis-2': Analysis(DOWN, ['analysis_1'], analysis_2),
}


class Node(object):

    def __init__(self):
        self.analysed_stuff = {}  # How will we initialize this in practice?

        # meaning: per analysis, over the current node and all its descendants, what's the latest change?

        # NOTE: if we have this mecahnism, do we need to have a global "something changed" tracking mechanism as well?
        # maybe that's superfluous then.
        self.recursive_times = {}

    def update(self, analysis_name, analysis_output, current_time):
        # only updates if the set value is actually new.

        if analysis_name not in self.analysed_stuff or self.analysed_stuff[analysis_name].output != analysis_output:
            self.analysed_stuff[analysis_name] = TimedOutput(current_time, analysis_output)
            return True

        return False


def get_next_analyses(analysis_graph, analyses_done, analyses_with_changed_outputs):
    return [a for a in analysis_graph.keys()
            if a not in analyses_done  # not already done
            and set(analysis_graph[a].dependencies) - analyses_done == set()  # all dependencies are done
            # there is a changed input:
            and analyses_with_changed_outputs.intersection(set(analysis_graph[a].dependencies)) != set()
            ]


def the_algo(tree, current_time):
    analyses_done = set()
    analyses_with_changed_outputs = set()

    # did the source-analysis change the outputs?
    # one answer could just be: that is assumed.

    next_analyses = get_next_analyses(analysis_graph, analyses_done, analyses_with_changed_outputs)
    while next_analyses != []:
        current_analysis = next_analyses[0]

        something_changed = do_analysis(all_kinnds_iof_stuff)

        analyses_done.add(current_analysis)
        if something_changed:
            analyses_with_changed_outputs.add(current_analysis)

        next_analyses = get_next_analyses(analysis_graph, analyses_done, analyses_with_changed_outputs)


def do_analysis(analysis, other_stuff):
    if analysis.direction == NONE:
        do_undirected_analysis(analysis)
    elif analysis.direction == UP:
        do_upwards_analysis(analysis)
    else:
        do_downwards_analysis(analysis)


def do_undirected_analysis(analysis, node, current_time):
    dependencies_are_reason_to_descend = False
    for a_name in analysis.dependencies:
        if node.recursive_times[a_name] == current_time:
            dependencies_are_reason_to_descend = True
            break

    dependencies_are_reason_for_work_at_this_level = False
    for a_name in analysis.dependencies:
        if node.analysed_stuff[a_name].time == current_time:
            dependencies_are_reason_for_work_at_this_level = True
            break

    # note: we do pre-order; might as well pick post-order, as long as we don't do the work twice.
    change_at_present_level = False

    if dependencies_are_reason_for_work_at_this_level:
        args = [node.analysed_stuff[a_name].output for a_name in analysis.dependencies]
        output = analysis.f(*args)
        change_at_present_level = node.update(analysis.name, output, current_time)

    any_lower_level_change = change_at_present_level

    if dependencies_are_reason_to_descend:
        for child in node.children:
            recursive_result = do_undirected_analysis(analysis, child, current_time)
            any_lower_level_change = any_lower_level_change or recursive_result

    if any_lower_level_change:
        node.recursive_times[analysis.name] = current_time

    return any_lower_level_change


def do_downwards_analysis(analysis, node, current_time, parent_changed, parent_output):
    dependencies_are_reason_to_descend = False
    for a_name in analysis.dependencies:
        if node.recursive_times[a_name] == current_time:
            dependencies_are_reason_to_descend = True
            break

    dependencies_are_reason_for_work_at_this_level = False
    for a_name in analysis.dependencies:
        if node.analysed_stuff[a_name].time == current_time:
            dependencies_are_reason_for_work_at_this_level = True
            break

    change_at_present_level = False

    # TODO: what if you're in initialization mode? i.e. the current value is not yet set?
    output = node.analysed_stuff[analysis.name].output  # i.e. the status quo;

    if dependencies_are_reason_for_work_at_this_level or parent_changed:
        args = [node.analysed_stuff[a_name].output for a_name in analysis.dependencies]
        output = analysis.f(parent_output, *args)
        change_at_present_level = node.update(analysis.name, output, current_time)

    any_lower_level_change = change_at_present_level

    if dependencies_are_reason_to_descend or change_at_present_level:
        for child in node.children:
            recursive_result = do_downwards_analysis(analysis, child, current_time, change_at_present_level, output)
            any_lower_level_change = any_lower_level_change or recursive_result

    if any_lower_level_change:
        node.recursive_times[analysis.name] = current_time

    return any_lower_level_change


def do_upwards_analysis(analysis, node, current_time, other_stuff_here_perhaps):
    dependencies_are_reason_to_descend = False
    for a_name in analysis.dependencies:
        if node.recursive_times[a_name] == current_time:
            dependencies_are_reason_to_descend = True
            break

    dependencies_are_reason_for_work_at_this_level = False
    for a_name in analysis.dependencies:
        if node.analysed_stuff[a_name].time == current_time:
            dependencies_are_reason_for_work_at_this_level = True
            break

    children_results = []

    if dependencies_are_reason_to_descend:
        for child in node.children:
            children_results.append(do_upwards_analysis(analysis, child, current_time))

    any_lower_level_change = any([cr[2] for cr in children_results])
    some_child_changed = any([cr[1] for cr in children_results])
    change_at_present_level = False

    output = node.analysed_stuff[analysis.name].output  # i.e. the status quo;

    if dependencies_are_reason_for_work_at_this_level or some_child_changed:
        args = [node.analysed_stuff[a_name].output for a_name in analysis.dependencies]

        children_outputs = [cr[0] for cr in children_results]
        output = analysis.f(children_outputs, *args)
        change_at_present_level = node.update(analysis.name, output, current_time)

    any_lower_level_change = any_lower_level_change or change_at_present_level

    if any_lower_level_change:
        node.recursive_times[analysis.name] = current_time

    return output, change_at_present_level, any_lower_level_change
