import functools
import os
import os.path as op
import logging
import tempfile

from abc import ABC, abstractmethod

import Bio
from kmtools import structure_tools, py_tools

logger = logging.getLogger(__name__)


class ToolError(ABC, Exception):
    pass


class _Tool(ABC):

    @property
    @abstractmethod
    def _result_slots(self):
        raise NotImplementedError

    @abstractmethod
    def __init__(self):
        self.result = py_tools.Struct(self._result_slots)
        self.cache = {}
        self.mutations = {}
        self.tempdir = op.join(tempfile.gettempdir(), self.__class__.__name__)
        os.makedirs(self.tempdir, exist_ok=True)

    def build(self):
        if not self.done:
            self._build()

    @abstractmethod
    def _build(self):
        raise NotImplementedError

    @property
    def done(self):
        return (all(key in self.result for key in self._result_slots) and
                all(op.isfile(self.result[key]) for key in self._result_slots
                    if key.endswith('file')))


class SequenceAnalyzer(_Tool):

    def __init__(self, sequence):
        super().__init__()
        assert len(sequence) > 0, "The sequence must not be empty!"
        self.sequence = sequence
        self._sequence_file = None

    @property
    def sequence_file(self):
        if self._sequence_file is None:
            self._sequence_file = op.join(self.tempdir, self.sequence.id + '.fasta')
            with open(self._sequence_file, 'wt') as ofh:
                Bio.SeqIO.write(self.sequence, ofh, 'fasta')
        return self._sequence_file

    @functools.lru_cache(maxsize=512)
    def analyze(self, mutation):
        assert self.done
        return self._analyze(self, mutation)

    @abstractmethod
    def _analyze(self, mutation):
        raise NotImplementedError


class StructureAnalyzer(_Tool):

    def __init__(self, structure):
        super().__init__()
        assert len(structure) == 1, "The structure must have only one model!"
        self.structure = structure
        self._structure_file = None

    @property
    def structure_file(self):
        if self._structure_file is None:
            self._structure_file = op.join(self.tempdir, self.structure.id + '.pdb')
            structure_tools.save_structure(self.structure, self._structure_file)
        return self._structure_file

    @functools.lru_cache(maxsize=512)
    def analyze(self, chain_id, residue_id, aa):
        assert self.done
        if isinstance(residue_id, int):
            residue_id = (' ', residue_id, ' ')
        return self._analyze(chain_id, residue_id, aa)

    @abstractmethod
    def _analyze(self, chain_id, residue_id, aa):
        raise NotImplementedError


class Modeller(_Tool):

    def __init__(self, structure):
        super().__init__()
        self.structure = structure
        self._structure_file = None

    @functools.lru_cache(maxsize=512)
    def mutate(self, mutation):
        """
        Returns
        -------
        Bio.PDB.Structure
        """
        return self._mutate(mutation)

    @abstractmethod
    def _mutate(self, mutation):
        raise NotImplementedError

    def model(self, alignment):
        """
        Returns
        -------
        Bio.PDB.Structure
        """
        return self._model(alignment)

    @abstractmethod
    def _model(self, alignment):
        raise NotImplementedError


class Analyzer(ABC):
    """Calculate structural properties for a PDB containing one or more chains.

    Runs the program POPS to calculate the interface size of the complexes
    This is done by calculating the surface of the complex and the seperated parts.
    The interface is then given by the substracting.
    """

    def __init__(self, pdb_file, working_dir, vdw_distance=5.0, min_contact_distance=4.0):
        self.pdb_file = pdb_file
        #: Folder with all the binaries (i.e. ./analyze_structure)
        self.working_dir = working_dir
        self.vdw_distance = vdw_distance
        self.min_contact_distance = min_contact_distance

        self._prepare_temp_folder(self.working_dir)

        self.sp = structure_tools.StructureParser()
        self.sp.extract(pdb_file)
        self.sp.save_structure(output_dir=self.working_dir)

        self.chain_ids = self.sp.chain_ids


class InterfaceAnalyzer(ABC):

    def __init__(self, structure, chain_1, residue_1, chain_2, residue_2):
        self.structure = structure
        self.chain_1 = chain_1
        self.residue_1 = residue_1
        self.chain_2 = chain_2
        self.residue_2 = residue_2
        self.tempdir = op.join(tempfile.gettempdir(), self.__class__.__name__)
        os.makedires(self.tempdir, exist_ok=True)

    def analyze(self):
        """
        Returns
        -------
        dict : Dictionary containing all the calculated features.
        """
        raise NotImplementedError