import sys
import quantum_fitter as qf
import numpy as np
import re
import os
import h5py


class LabberData:
    def __init__(self, filePath=None, channelName=None, powerName:str=None, frequencyName=None, mode='resonator'):
        self._filePath = filePath

        self.h5data = h5py.File(self._filePath, 'r')

        self._channelName, self._channelMatrix, self._dataXMatrix, self._dataYMatrix = list(), None, None, None
        self._numData = None

        # fit data is an NxM matrix (N is the number id)
        self._rawData, self._fitData, self._fitMask, self._fitID = None, None, None, None

        self._fitParamHistory, self._fitValueHistory = None, None
        self.mode = None

    def pull_data(self, mode='resonator', **kwargs):
        """
        Pull the data from labber file by certain frequency and power.
        :param mode: the pulling mode
        :param power:
        :param frequency:
        :return:
        """
        if mode == 'resonator':
            self.mode = mode
            # print(self.h5data['Data']['Data'][1,2,:])


            self._channelMatrix = self.h5data['Data']['Data'][:]
            self._dataXMatrix = self.h5data['Traces']['VNA - S21_t0dt'][:]
            self._dataYMatrix = self.h5data['Traces']['VNA - S21'][:]
            self._dataYMatrix = np.vectorize(complex)(self._dataYMatrix[:, 0, :], self._dataYMatrix[:, 1, :]).T
            self._fitMask = np.zeros((self._dataYMatrix.shape[1]), dtype=bool)

            if kwargs:
                print('Here it goes')
                self.mask_data(**kwargs)

    def mask_data(self, **kwargs):
        for i in range(len(self.h5data['Data']['Channel names'][:])):
            self._channelName.append(self.h5data['Data']['Channel names'][i][0].decode("utf-8"))
        self._numData = self.h5data['Traces']['VNA - S21_N'][0]

        channelMatrixNum = len(self._channelMatrix.shape) - 1
        channelNameNum = len(self._channelName)

        for key in kwargs:
            channelNo = LabberData.find_str_args(self._channelName, key)
            for p in kwargs[key]:
                dataID = np.argwhere(self._channelMatrix == p)
                dataID.
                dataID = (dataID[:, 2] + 1) * dataID[:, 0]
                self._fitMask[dataID] = True

            pass

        if power:
            power = np.array(power, dtype=float).reshape([-1])
        if frequency:
            frequency = np.array(frequency, dtype=float).reshape([-1])

        for p in np.concatenate((power, frequency)):
            dataID = np.argwhere(self._channelMatrix == p)
            dataID = (dataID[:, 2] + 1) * dataID[:, 0]
            self._fitMask[dataID] = True

        self._fitID = np.argwhere(self._fitMask == True).flatten()

        # Extract the needed data

    def fit_data(self, model='ResonatorModel'):
        self._dataXMatrix *= 1e-6  # Change to MHz

        for id in self._fitID:
            t_n = qf.QFit(self.altspace(self._dataXMatrix[id]), self._dataYMatrix[id], model)
            t_n.filter_guess(level=5)
            t_n.do_fit()
            self._fitParamHistory.append(t_n.fit_params())
            self._fitValueHistory.append(t_n.fit_values())
        self._fitValueHistory = np.array(self._fitValueHistory)
        return t_n

    def push_data(self, filepath=None, filename=None, labber_path=None):
        if labber_path:
            sys.path.append(labber_path)
        try:
            import Labber
        except:
            print('No labber found here!')

        if self.mode == 'resonator':

            _LogFile = Labber.LogFile(self._filePath)

            if not filename:
                if not filepath:
                    filename = 'Fit_data_'+get_file_name_from_path(self._filePath)
                    filename = filename.replace('.hdf5', '')

                    filepath = 'D:/LabberDataTest'

            _Qi = np.repeat([x['Qi'] for x in self._fitParamHistory], 2) * 1e3
            # self._Qi = self._Qi.reshape((2 * len(self._fitEntry), -1))
            _Qe = np.repeat([x['Qe_mag'] for x in self._fitParamHistory], 2) * 1e3

            _FitLogFile = Labber.createLogFile_ForData(filename,
            [dict(name='S21', unit='dB', vector=True, complex=True),
            dict(name='Frequency', unit='GHz')],
             [dict(name='Center Frequency', unit='GHz', values=self._selectCenterFrequency),
             dict(name='Output Power', unit='dB', values=self._selectPower),
              dict(name='Qi', unit='', values=_Qi),
              dict(name='Qe', unit='', values=_Qe),
            ])

            for _entry in range(len(self._fitEntry)):
                _fitDictForAdd = _LogFile.getEntry(entry=self._fitEntry[_entry])[self._channelName]
                # _fitDictForAdd[self._channelName]['y'] = self._fitValueHistory[_entry]

                _fitDictForAdd = Labber.getTraceDict(self._fitValueHistory[_entry],
                                _LogFile.getEntry(entry=self._fitEntry[_entry])[self._channelName]['t0'],
                             _LogFile.getEntry(entry=self._fitEntry[_entry])[self._channelName]['t0'])

                # Add raw data
                _data = {'S21': self.S21[_entry],
                         'Frequency': self.frequency[_entry] * 1e-3,
                         }

                _FitLogFile.addEntry(_data)

                # Add fit data
                _data = {'S21': self._fitValueHistory[_entry],
                         'Frequency': self.frequency[_entry] * 1e-3,
                         }
                _FitLogFile.addEntry(_data)

            LabberData._data_structure_change(_FitLogFile.getFilePath(0), 3, self._Qi)
            LabberData._data_structure_change(_FitLogFile.getFilePath(0), 4, self._Qe)

    @staticmethod
    def _data_structure_change(self, path, row, data):
        """
        The aim here is to modify the h5 file to better display the fitting parameters.
        :param path: The h5 file path
        :param row: The column index in the ['Data']['Data']
        :return: None
        """
        h5 = h5py.File(path, 'r+')
        print(h5['Data']['Data'])
        h5['Data']['Data'][:, row, :] = data

    @staticmethod
    def altspace(t0dt, count, **kwargs):
        start = t0dt[0]
        step = t0dt[1]
        stop = start + (step * count)
        return np.linspace(start, stop, count, endpoint=False)

    @staticmethod
    def find_str_args(choices: list, target):
        for i in range(len(choices)):
            if target in choices[i].lower():
                return i
            else:
                print('Didn\'t find the corresponding channel')


def get_file_name_from_path(path):
    import os
    head, tail = os.path.split(path)
    return tail

