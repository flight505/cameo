# Copyright 2014 Novo Nordisk Foundation Center for Biosustainability, DTU.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import Queue

from uuid import uuid1
from pandas import DataFrame
from cameo import config
from cameo.strain_design.heuristic.multiprocess.observers import AbstractParallelObserver, \
    AbstractParallelObserverClient
if config.use_bokeh:
    from bokeh.plotting import *


class IPythonNotebookBokehMultiprocessPlotObserver(AbstractParallelObserver):

    __name__ = "IPythonNotebookBokehMultiprocessPlot"

    def __init__(self, url='default', color_map={}, *args, **kwargs):
        super(IPythonNotebookBokehMultiprocessPlotObserver, self).__init__(*args, **kwargs)
        self.url = url
        self.plotted = False
        self.connections = {}
        self.color_map = color_map
        self.data_frame = DataFrame(columns=['iteration', 'island', 'color', 'fitness'])

    def _create_client(self, i):
        self.clients[i] = IPythonNotebookBokehMultiprocessPlotObserverClient(queue=self.queue, index=i)

    def start(self):
        AbstractParallelObserver.start(self)
        self._plot()

    def _plot(self):
        self.plotted = True
        self.uuid = uuid1()
        output_notebook(url=self.url, docname=str(self.uuid))
        figure()
        scatter([], [], title="Best solution convergence plot", tools='',
                color=self.color_map, fill_alpha=0.2, size=7)

        xaxis()[0].axis_label = "Iteration"
        yaxis()[0].axis_label = "Fitness"

        self.plot = curplot()
        renderer = [r for r in self.plot.renderers if isinstance(r, Glyph)][0]
        self.ds = renderer.data_source
        show()

    def _process_message(self, message):
        if not self.plotted:
            self._plot()

        index = message['index']
        df = DataFrame({
            'iteration': [message['iteration']],
            'fitness': [message['fitness']],
            'color': [self.color_map[index]],
            'island': [index]
        })
        self.data_frame = self.data_frame.append(df, ignore_index=True)
        if message['iteration'] % message['n'] == 0:
            self._update_plot()

    def _update_plot(self):
        self.ds.data['x'] = self.data_frame['iteration']
        self.ds.data['y'] = self.data_frame['fitness']
        self.ds.data['fill_color'] = self.data_frame['color']
        self.ds.data['line_color'] = self.data_frame['color']
        self.ds._dirty = True
        session().store_obj(self.ds)

    def stop(self):
        self.data_frame = DataFrame(columns=['iteration', 'island', 'color', 'fitness'])
        self.plotted = False


class IPythonNotebookBokehMultiprocessPlotObserverClient(AbstractParallelObserverClient):

    __name__ = "IPython Notebook Bokeh Multiprocess Plot Observer"

    def __init__(self, *args, **kwargs):
        super(IPythonNotebookBokehMultiprocessPlotObserverClient, self).__init__(*args, **kwargs)
        self.iteration = 0

    def __call__(self, population, num_generations, num_evaluations, args):
        self.iteration += 1
        best = max(population)
        try:
            self._queue.put_nowait({
                'fitness': best.fitness,
                'iteration': self.iteration,
                'index': self.index,
                'n': args.get('n', 1)})
        except Queue.Full:
            pass

    def reset(self):
        self.iteration = 0

    def close(self):
        self.connection.close()


class IPythonNotebookBokehMultiprocessParetoPlotObserver(IPythonNotebookBokehMultiprocessPlotObserver):

    __name__ = "IPythonNotebookBokehMultiprocessParetoPlot"

    def __init__(self, objective_functions=None, x=1, y=1, *args, **kwargs):
        super(IPythonNotebookBokehMultiprocessParetoPlotObserver, self).__init__(*args, **kwargs)
        self.x = x
        self.y = y
        self.ofs = objective_functions

    def _create_client(self, i):
        self.clients[i] = IPythonNotebookBokehMultiprocessParetoPlotObserverClient(queue=self.queue, index=i)

    def _plot(self):
        self.plotted = True
        self.uuid = uuid1()
        output_notebook(url=self.url, docname=str(self.uuid))
        figure()
        scatter([], [], title="Pareto plot", tools='',
                color=self.color_map, fill_alpha=0.2, size=7)
        xaxis()[0].axis_label = self.ofs[self.x].name
        yaxis()[0].axis_label = self.ofs[self.y].name

        self.plot = curplot()
        renderer = [r for r in self.plot.renderers if isinstance(r, Glyph)][0]
        self.ds = renderer.data_source
        show()

    def _update_plot(self):
        self.ds.data['x'] = [f[self.x] for f in self.data_frame['fitness']]
        self.ds.data['y'] = [f[self.y] for f in self.data_frame['fitness']]
        self.ds.data['fill_color'] = self.data_frame['color']
        self.ds.data['line_color'] = self.data_frame['color']
        self.ds._dirty = True
        session().store_obj(self.ds)


class IPythonNotebookBokehMultiprocessParetoPlotObserverClient(AbstractParallelObserverClient):

    __name__ = "IPython Notebook Bokeh Multiprocess Pareto Plot Observer"

    def __init__(self, *args, **kwargs):
        super(IPythonNotebookBokehMultiprocessParetoPlotObserverClient, self).__init__(*args, **kwargs)
        self.iteration = 0

    def __call__(self, population, num_generations, num_evaluations, args):
        self.iteration += 1
        try:
            self._queue.put_nowait({
                'fitness': [i.fitness for i in population],
                'iteration': self.iteration,
                'index': self.index,
                'n': args.get('n', 1)})
        except Queue.Full:
            pass

    def reset(self):
        self.iteration = 0

    def close(self):
        self.connection.close()

