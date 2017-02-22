import logging
import os
import os.path as op
import shutil

from kmtools import system_tools

import elaspic
from elaspic.tools._abc import ToolError

logger = logging.getLogger(__name__)


class FoldxError(ToolError):
    pass


class FoldX:

    _names_stability = [
        ('dg', 1),  # totalEnergy
        ('backbone_hbond', 2),
        ('sidechain_hbond', 3),
        ('van_der_waals', 4),
        ('electrostatics', 5),
        ('solvation_polar', 6),
        ('solvation_hydrophobic', 7),
        ('van_der_waals_clashes', 8),
        ('entropy_sidechain', 9),
        ('entropy_mainchain', 10),
        ('sloop_entropy', 11),
        ('mloop_entropy', 12),
        ('cis_bond', 13),
        ('torsional_clash', 14),
        ('backbone_clash', 15),
        ('helix_dipole', 16),
        ('water_bridge', 17),
        ('disulfide', 18),
        ('electrostatic_kon', 19),
        ('partial_covalent_bonds', 20),
        ('energy_ionisation', 21),
        ('entropy_complex', 22),
        ('number_of_residues', 23)]
    names_stability_wt = (
        [name + '_wt' for name, position in _names_stability[:-1]] +
        ['number_of_residues'])
    names_stability_mut = (
        [name + '_mut' for name, position in _names_stability[:-1]] +
        ['number_of_residues'])

    _names_stability_complex = (
        [('intraclashes_energy_1', 3), ('intraclashes_energy_2', 4), ] +
        [(name, position + 4) for name, position in _names_stability])
    names_stability_complex_wt = (
        [name + '_wt' for name, position in _names_stability_complex[:-1]] +
        ['number_of_residues'])
    names_stability_complex_mut = (
        [name + '_mut' for name, position in _names_stability_complex[:-1]] +
        ['number_of_residues'])

    def __init__(self, pdb_file, chain_id):
        """
        """
        self.pdb_filename = op.basename(pdb_file)
        self.chain_id = chain_id
        self.foldx_runfile = op.join(self.tempdir, 'runfile_FoldX.txt')

    def _build(self):
        protein_id = self.sequence_seqrecords[sequence_idx].id
        chain_id = self.modeller_structure.child_list[0].child_list[sequence_idx].id

        mutation_errors = ''

        # Domain definitions, in case not the entire sequence was modelled
        domain_def_offset = self.modeller_results['domain_def_offsets'][sequence_idx]
        domain_def = self.modeller_results['model_domain_defs'][sequence_idx]
        logger.debug("domain_def_offset: %s", domain_def_offset)
        logger.debug("domain_def: %s", domain_def)
        # domain_def = (
        #     domain_def_offset[0],
        #     len(self.sequence_seqrecords[sequence_idx].seq) - domain_def_offset[1]
        # )

        mutation_pos = int(mutation[1:-1]) - domain_def[0] + 1
        if mutation_pos > (domain_def[1] - domain_def[0] + 1):
            raise elaspic.exc.MutationOutsideDomainError()

        position_modeller = (
            structure_tools.convert_position_to_resid(
                self.modeller_structure[0][chain_id],
                [mutation_pos])[0]
        )
        mutation_modeller = (mutation[0] + str(position_modeller) + mutation[-1])
        logger.debug('mutation: {}'.format(mutation))
        logger.debug('position_modeller: {}'.format(position_modeller))
        logger.debug('mutation_modeller: {}'.format(mutation_modeller))

        if len(self.sequence_seqrecords) == 1:
            partner_chain_idx = None
            partner_protein_id = ''
            partner_chain_id = None
        else:
            # TODO: slight hack getting partner_chain_idx
            partner_chain_idx = [
                i for i in range(len(self.sequence_seqrecords)) if i != sequence_idx
            ][0]
            partner_protein_id = self.sequence_seqrecords[partner_chain_idx].id
            partner_chain_id = (
                self.modeller_structure.child_list[0].child_list[partner_chain_idx].id
            )
            logger.debug('sequence_idx: {}'.format(sequence_idx))
            logger.debug('partner_chain_idx: {}'.format(partner_chain_idx))
            if sequence_idx == 0:
                logger.debug('interacting_aa_1: {}'.format(self.interacting_aa_1))
                if int(mutation[1:-1]) not in self.interacting_aa_1:
                    raise elaspic.exc.MutationOutsideInterfaceError()
            elif sequence_idx == 1:
                logger.debug('interacting_aa_2: {}'.format(self.interacting_aa_2))
                if int(mutation[1:-1]) not in self.interacting_aa_2:
                    raise elaspic.exc.MutationOutsideInterfaceError()
            else:
                logger.warning(
                    "Can't make sure that a mutation is inside an interface if there are only "
                    "two chains!"
                )

        mutation_id = '{}-{}-{}'.format(protein_id, partner_protein_id, mutation)

        if mutation_errors:
            results = dict(
                protein_id=protein_id,
                sequence_idx=sequence_idx,
                chain_modeller=chain_id,
                partner_chain_id=partner_chain_id,
                mutation_id=mutation_id,
                mutation_domain=mutation,
                mutation_errors=mutation_errors,
            )
            self.mutations[(sequence_idx, mutation)] = results
            return results

        # ...
        logger.debug('Running mutation with mutation_id: {}'.format(mutation_id))
        logger.debug('chain_id: {}'.format(chain_id))
        logger.debug('partner_chain_id: {}'.format(partner_chain_id))

        #######################################################################
        # Create a folder for all mutation data.
        mutation_dir = op.join(elaspic.CONFIGS['model_dir'], 'mutations', mutation_id)
        os.makedirs(mutation_dir, exist_ok=True)
        os.makedirs(mutation_dir, exist_ok=True)
        shutil.copy(op.join(elaspic.CONFIGS['data_dir'], 'rotabase.txt'), mutation_dir)

        #######################################################################
        # Copy the homology model to the mutation folder
        model_file = op.join(mutation_dir, op.basename(self.modeller_results['model_file']))
        shutil.copy(
            op.join(elaspic.CONFIGS['unique_temp_dir'], self.modeller_results['model_file']),
            model_file)

        #######################################################################
        # 2nd: use the 'Repair' feature of FoldX to optimise the structure
        fX = elaspic.tools.FoldX(model_file, chain_id, mutation_dir)
        repairedPDB_wt = fX('RepairPDB')

    def _mutate(self):

        #######################################################################
        # Introduce the mutation using FoldX
        mutCodes = [mutation_modeller[0] + chain_id + mutation_modeller[1:], ]
        logger.debug('Mutcodes for foldx: {}'.format(mutCodes))

        # Introduce the mutation using foldX
        fX_wt = elaspic.tools.FoldX(repairedPDB_wt, chain_id, mutation_dir)
        repairedPDB_wt_list, repairedPDB_mut_list = fX_wt('BuildModel', mutCodes)

        logger.debug('repairedPDB_wt_list: %s' % str(repairedPDB_wt_list))
        logger.debug('repairedPDB_mut_list: %s' % str(repairedPDB_mut_list))

        wt_chain_sequences = structure_tools.get_structure_sequences(repairedPDB_wt_list[0])
        mut_chain_sequences = structure_tools.get_structure_sequences(repairedPDB_mut_list[0])

        logger.debug('wt_chain_sequences: %s' % str(wt_chain_sequences))
        logger.debug('mut_chain_sequences: %s' % str(mut_chain_sequences))

        # Copy the foldX wildtype and mutant pdb files (use the first model if there are multiple)
        model_file_wt = op.join(mutation_dir, mutation_id + '-wt.pdb')
        model_file_mut = op.join(mutation_dir, mutation_id + '-mut.pdb')
        shutil.copy(repairedPDB_wt_list[0], model_file_wt)
        shutil.copy(repairedPDB_mut_list[0], model_file_mut)

        #######################################################################
        # 4th: set up the classes for the wildtype and the mutant structures
        fX_wt_list = list()
        for wPDB in repairedPDB_wt_list:
            fX_wt_list.append(elaspic.tools.FoldX(wPDB, chain_id, mutation_dir))

        fX_mut_list = list()
        for mPDB in repairedPDB_mut_list:
            fX_mut_list.append(elaspic.tools.FoldX(mPDB, chain_id, mutation_dir))

        #######################################################################
        # 5th: Calculate energies
        assert len(fX_wt_list) == 1
        stability_values_wt = ','.join(
            '{}'.format(f) for f in fX_wt_list[0]('Stability')
        )
        assert len(fX_wt_list) == 1
        stability_values_mut = ','.join(
            '{}'.format(f) for f in fX_mut_list[0]('Stability')
        )

        if len(self.sequence_seqrecords) == 1:
            complex_stability_values_wt = None
            complex_stability_values_mut = None
        else:
            assert len(fX_wt_list) == 1
            complex_stability_values_wt = ','.join(
                '{}'.format(f) for f in fX_wt_list[0]('AnalyseComplex')
            )
            assert len(fX_mut_list) == 1
            complex_stability_values_mut = ','.join(
                '{}'.format(f) for f in fX_mut_list[0]('AnalyseComplex')
            )

    def _model(self):
        raise NotImplementedError

    # ========= Helper methods ==========

    template = """\
<TITLE>FOLDX_runscript;
<JOBSTART>#;
<PDBS>{pdb_file};
<BATCH>#;
<COMMANDS>FOLDX_commandfile;
{command_line};
<END>#;
<OPTIONS>FOLDX_optionfile;
<Temperature>298;
<R>#;
<pH>7;
<IonStrength>0.050;
<numberOfRuns>{number_of_runs};
<water>{water};
<metal>-CRYSTAL;
<VdWDesign>2;
<pdb_waters>false;
<OutPDB>{output_pdb};
<pdb_hydrogens>false;
<END>#;
<JOBEND>#;
<ENDFILE>#;
"""

    def _run(self, pdb_file, chain_id, whatToRun, mutCodes=[]):
        """
        Select which action should be performed by FoldX by setting `whatToRun`.

        Possible values are:

            - AnalyseComplex
            - Stability
            - RepairPDB
            - BuildModel

        See the `FoldX manual`_ for an explanation on what they do.

        .. _FoldX manual: http://foldx.crg.es/manual3.jsp
        """
        logger.debug('Running FoldX {}'.format(whatToRun))
        filename = self._write_runfile(chain_id, whatToRun, mutCodes)
        self._run_runfile()
        return self._read_results()

    def _get_foldx_config_file(self, chainID, whatToRun, mutCodes):
        if whatToRun == 'AnalyseComplex':
            copy_filename = 'run-analyseComplex.txt'
            command_line = '<AnalyseComplex>AnalyseComplex_resultFile.txt,{chainID}'\
                .format(chainID=chainID)
            output_pdb = 'false'
        elif whatToRun == 'Stability':
            copy_filename = 'run-stability.txt'
            command_line = '<Stability>Stability.txt'
            output_pdb = 'false'
        elif whatToRun == 'RepairPDB':
            copy_filename = 'run-repair.txt'
            command_line = '<RepairPDB>#'
            output_pdb = 'true'
        elif whatToRun == 'BuildModel':
            copy_filename = 'run-build.txt'
            # file_with_mutations = 'mutant_file.txt'
            file_with_mutations = 'individual_list.txt'
            with open(op.join(self.tempdir, file_with_mutations), 'w') as fh:
                fh.writelines(','.join(mutCodes) + ';\n')
            command_line = '<BuildModel>BuildModel,{file_with_mutations}'\
                .format(file_with_mutations=file_with_mutations)
            output_pdb = 'true'

    def _foldx_repair_pdb(self):
        foldx_
FoldX --command=RepairPDB --pdb=RP.pdb


    def _foldx_build_model(self):
        ....

    def _foldx_stability(self):
        ...

    def _foldx_analyse_complex(self):
        ...





FoldX --command=Optimize --pdb=OP.pdb


).format(
                pdb_file=self.structure_file,
                command_line=command_line,
                number_of_runs=elaspic.CONFIGS.get('foldx_num_of_runs', 1),
                water=elaspic.CONFIGS.get('foldx_water', '-IGNORE'),
                output_pdb=output_pdb)

        # This just makes copies of the runfiles for debugging...
        with open(self.foldx_runfile, 'w') as f:
            f.write(foldX_runfile)
        shutil.copy(self.foldx_runfile, op.join(self.tempdir, copy_filename))



"""
foldx

"""


    def _run_runfile(self):
        """.

        .. todo:: Add a fallback plan using libfaketime.
        """
        import faketime.config
        # system_command = './FoldX.linux64 -runfile ' + self.foldx_runfile
        system_command = "foldx -runfile '{}'".format(self.foldx_runfile)
        logger.debug("FoldX system command: '{}'".format(system_command))
        env = os.environ.copy()
        env['LD_PRELOAD'] = faketime.config.libfaketime_so_file
        env['FAKETIME'] = '2015-12-26 00:00:00'
        p = system_tools.run(system_command, cwd=self.tempdir, env=env)
        if p.stderr.strip():
            logger.debug('foldx result:\n{}'.format(p.stdout.strip()))
            logger.error('foldx error message:\n{}'.format(p.stderr.strip()))
            if 'Cannot allocate memory' in p.stderr:
                raise elaspic.exc.ResourceError(p.stderr)
        if 'There was a problem' in p.stdout:
            logger.error('foldx result:\n{}'.format(p.stdout.strip()))
            if 'Specified residue not found.' in p.stdout:
                raise elaspic.exc.MutationMismatchError()

    def _read_result(self, what_to_run):
        if what_to_run == 'AnalyseComplex':
            return self._read_result(
                op.join(self.tempdir, 'Interaction_AnalyseComplex_resultFile.txt'), what_to_run)
        elif what_to_run == 'Stability':
            return self._read_result(
                op.join(self.tempdir, 'Stability.txt'), what_to_run)
        elif what_to_run == 'RepairPDB':
            return op.join(self.tempdir, 'RepairPDB_' + self.pdb_filename)
        elif what_to_run == 'BuildModel':
            # see the FoldX manual for the naming of the generated structures
            if elaspic.CONFIGS['foldx_num_of_runs'] == 1:
                mutants = [op.join(self.tempdir, self.pdb_filename[:-4] + '_1.pdb'), ]
                wiltype = [op.join(self.tempdir, 'WT_' + self.pdb_filename[:-4] + '_1.pdb'), ]
                results = [wiltype, mutants]
            else:
                mutants = [
                    op.join(self.tempdir, self.pdb_filename[:-4] + '_1_' + str(x) + '.pdb')
                    for x in range(0, elaspic.CONFIGS['foldx_num_of_runs'])
                ]
                wiltype = [
                    op.join(
                        self.tempdir,
                        'WT_' + self.pdb_filename[:-4] + '_1_' + str(x) + '.pdb')
                    for x in range(0, elaspic.CONFIGS['foldx_num_of_runs'])
                ]
                results = [wiltype, mutants]
            return results

    def _read_result(self, outFile, whatToRead):
        with open(outFile, 'r') as f:
            lines = f.readlines()
            line = lines[-1].split('\t')
            if whatToRead == 'BuildModel':
                total_energy_difference = line[1]
                return total_energy_difference
            if whatToRead == 'Stability':
                stability_values = [
                    line[x[1]].strip() for x in self.names_rows_stability
                ]
                return stability_values
            if whatToRead == 'AnalyseComplex':
                complex_stability_values = [
                    line[x[1]].strip() for x in self.names_rows_stability_complex
                ]
                return complex_stability_values
