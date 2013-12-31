# -*- coding: utf-8 -*-
"""
Created on Thu May  2 17:25:45 2013

@author: niklas
"""

from class_pdbTemplate import pdbTemplate
import class_callTcoffee as tc
import class_error as error

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.PDB.PDBParser import PDBParser

#from Bio.Align import MultipleSeqAlignment

import gzip
from math import sqrt
from math import fabs
import logging

class get_template():
    """
    Parent class holding functions for finding the correct template given a
    uniprot sequence
    """
    def __init__(self, tmpPath, unique, pdbPath, savePDB, saveAlignments, pool, semaphore, get_uniprot_seq, get_resolution, log):
        """
        input:
        tmpPath             type 'str'
        unique              type 'str'
        pdbPath             type 'str'
        savePDB             type 'str'
        saveAlignments      type 'str'
        pool                type class '__main__.ActivePool'
        semaphore           type class 'multiprocessing.synchronize.Semaphore'
        get_uniprot_seq     type __main__.getUniprotSequence instance
        """
        self.tmpPath = tmpPath
        self.unique = unique + '/'
        self.pdbPath = pdbPath
        self.savePDB = savePDB
        self.saveAlignments = saveAlignments
        self.pool = pool
        self.semaphore = semaphore
        
        self.get_uniprot_seq = get_uniprot_seq
        
        self.get_resolution = get_resolution
        
        # get the logger from the parent and add a handler
        self.log = log
    
    def make_SeqRec_object(self, sequence, domain, ID):
        """
        return a Biopython SeqRec object
        cuts the sequence (given as string) to the domain boundaries and sets the ID
        
        input:
        sequence    type class 'Bio.SeqRecord.SeqRecord' or str
        domain      type 'list' of int
        ID          type 'str'

        return      type class 'Bio.SeqRecord.SeqRecord'
        """
        
        if isinstance(sequence, SeqRecord):
            sequence = sequence[domain[0]-1:domain[1]]
        elif isinstance(sequence, Seq):
            sequence = SeqRecord(sequence[domain[0]-1:domain[1]])
        elif isinstance(sequence, str):
            sequence = SeqRecord(Seq(sequence[domain[0]-1:domain[1]]))
        sequence.id = ID

        return sequence
    
#    def close(self):
#        self.get_uniprot_seq.close()
    
    ##############
    # for map_to_uniprot
    #
    def map_to_uniprot(self, uniprotKB, uniprot_sequence, domain_uniprot, pdbCode, chain, domain_pdb, saveAlignments, refine):
        """
        Align the uniprot and the pdb sequence 
        
        
        input:
        uniprotKB           type 'str'
        uniprot_sequence    type class 'Bio.SeqRecord.SeqRecord'
        domain_uniprot      type 'list' of 'int'
        pdbCode             type 'str'
        chain               type 'str'
        domain_pdb          type 'list' of 'int'
        saveAlignments      type 'str'
        refine              type 'bool'
        
        
        return:
        alignment           class 'Bio.Align.MultipleSeqAlignment'
        score               type 'float'
        pdb_sequence_id     type 'str'
        domain_uniprot      type 'list' of 'int'

        """
        # 1st: cut the uniprot sequence to the domain boundaries
        # 2nd: check if the uniprot sequences "overlaps", if yes, extend domain
        #      and repeat alignment

        
        # get the sequence from the pdb
        pdb_sequence, domain_pdb, chainNumberingDomain = self.get_pdb_sequence(pdbCode, chain, domain_pdb)
        
        
        
        # get the uniprot sequence
        uniprot_sequence_domain = self.make_SeqRec_object(uniprot_sequence, domain_uniprot, uniprotKB)
        
        # get the alignment
        alignment, score, pdb_sequence_id = self.map_to_uniprot_helper(uniprot_sequence_domain, pdb_sequence, saveAlignments)


        
        # AS Start ############################################################
        # It was assumed that the uniprot domain boundaries are expanded and are correct.
        # However when using pfamscan output, this assumption is not correct.
        
        domain_uniprot_expanded = self.expand_boundaries(alignment, domain_uniprot, )
        
        
        # AS End ##############################################################


        
        # if it is the last round optimise the alignment
        if refine:
            alignment, score, cut_uniprot, cut_pdb = self.align_shorten(alignment, score, pdb_sequence_id, saveAlignments)
            domain_uniprot = [ domain_uniprot[0] + cut_uniprot[0], domain_uniprot[1] - cut_uniprot[1] ]


        return alignment, score, pdb_sequence_id, domain_uniprot


    def map_to_uniprot_helper(self, uniprot_sequence, pdb_sequence, saveAlignments):
        """
        input:
        uniprot_sequence    type class 'Bio.SeqRecord.SeqRecord'
        pdb_sequence        type class 'Bio.SeqRecord.SeqRecord'
        saveAlignments      type 'str'
        
        return:
        alignment           type class 'Bio.Align.MultipleSeqAlignment'
        score               type 'float'
        pdb_sequence.id     type 'str'
        """
        # write both sequences to one file
        seqFiles = open(self.tmpPath + self.unique + 'seqfiles.fasta', 'w')
        SeqIO.write([uniprot_sequence, pdb_sequence], seqFiles, 'fasta')
        seqFiles.close()
        
        seqIDs = [uniprot_sequence.id, pdb_sequence.id]
        
        # do the alignment and get the score
        alignment, score = self.do_align(seqIDs, saveAlignments)

        return alignment, score, pdb_sequence.id
        
        
        
    def expand_boundaries(self, alignment, domain_uniprot, ):
        """
        AS:
        
        input:
        
        output:
        
        """
        start = domain_uniprot[0]
        end = domain_uniprot[1]
        
        
        # subtract number of dashes from start, add number of dashes to end
        
        
        return 
        
    
    
    def do_align(self, seqIDs, saveAlignments):
        """
        Align the sequences in the seqFile.fasta file and return the alignment
        and the percentage identity
        
        input
        seqIDs              type 'list'     ;look like ['P01112', '1FOEB']
        saveAlignments      type 'str'
        
        
        alignments[0]       type class 'Bio.Align.MultipleSeqAlignment'
        score               type 'float'
        """
        # use the try statement to ensure that the sempaphore is released
        # in the end
        try:
            with self.semaphore:
                # register to keep track of the running t_coffee instances
                # the maximal number is set in the configfile.
                self.pool.makeActive(self.unique)
                self.log.debug("Aligning: " + seqIDs[0] + ':' + seqIDs[1])
                tcoffee = tc.tcoffee_alignment(self.tmpPath, 
                                               self.unique,
                                               saveAlignments, 
                                               [self.tmpPath + self.unique + 'seqfiles.fasta', ], 
                                               seqIDs, 
                                               )
                alignments = tcoffee.align()
        except:
            raise
        finally:
                self.pool.makeInactive(self.unique)
        
        self.log.debug("Done aligning: " + seqIDs[0] + ':' + seqIDs[1])
        # see http://www.nature.com/nmeth/journal/v10/n1/full/nmeth.2289.html#methods
        # getting the score like Aloy did, based on sequence identity and coverage
        score_id = self.get_identity(alignments[0])
        score_cov = self.get_coverage(alignments[0])
        a = 0.95
        score = a*score_id/100.0 * score_cov/100 + (1.0-a)*score_cov/100
        return alignments[0], score
        
        

    def get_sequence_from_alignment(self, aligned_sequence):
        """
        Removes the gaps (i.e. '-') from the sequence and creates a
        Biopython SeqRecord object.
        
        input:
        aligned_sequence    type class 'Bio.SeqRecord.SeqRecord'

        return:
                            type class 'Bio.SeqRecord.SeqRecord'
        """
        seq = ''
        for i in range(len(aligned_sequence)):
            if aligned_sequence[i] != '-':
                seq = seq + aligned_sequence[i]
        result      = SeqRecord(Seq(seq))
        result.id   = aligned_sequence.id
        result.name = aligned_sequence.name

        return result
    
    
    def check_for_loners(self, uniprot_alignment, pdb_alignment, left_or_right):
        """
        For a quality control of the alignment 
        
        input:
        uniprot_alignment   type class 'Bio.SeqRecord.SeqRecord'
        pdb_alignment       type class 'Bio.SeqRecord.SeqRecord'
        left_or_right       type 'str'
        
        return:
                            type class 'Bio.SeqRecord.SeqRecord', 'str'
        """
        # first check for which sequence to check
        if left_or_right == 'left':
            for i in range(len(uniprot_alignment)):
                if uniprot_alignment[i] == '-':
                    return uniprot_alignment, 'pdb'
                elif pdb_alignment[i] == '-':
                    return pdb_alignment, 'uniprot'
        elif left_or_right == 'right':
            for i in range(len(uniprot_alignment)-1,-1,-1):
                if uniprot_alignment[i] == '-':
                    return uniprot_alignment, 'pdb'
                elif pdb_alignment[i] == '-':
                    return pdb_alignment, 'uniprot'
        else:
            print 'You must specify left or right correctly!'
            return


            
        
    def align_shorten(self, alignment, score, pdb_sequence_id, saveAlignments):
        """
        T-Coffee has an issue where it is placing some amino acids strangely
        far away from the main central block. That looks something like this:
            
            AA-------TTTT-XXXXXXXX---       pdb sequence
            XXXXXXXXXXXXXXXXXXXX-XXXX       uniprot sequence
        
        In such a case it is advisable to shorten the uniprot sequence to get
        a better alignment.
        
        input:
        alignment               type class 'Bio.Align.MultipleSeqAlignment'
        score                   type 'float'
        pdb_sequence_id         type 'str'
        saveAlignments          type 'str'
        
        
        return:
        alignment               type class 'Bio.Align.MultipleSeqAlignment'
        score                   type 'float'
        cut_left_all_uniprot    type 'int'
        cut_right_all_uniprot   type 'int'
        cut_left_all_pdb        type 'int'
        cut_right_all_pdb       type 'int'
        """

        uniprot_alignment, pdb_alignment = self.pick_sequence(alignment, pdb_sequence_id)

        cut_left_all_uniprot = 0
        cut_right_all_uniprot = 0
        cut_left_all_pdb = 0
        cut_right_all_pdb = 0
        
        # shorten as long as the alignment appears to have to large gaps
        cut = True
        while cut:
            cut, cut_left, cut_right, uniprot_or_pdb_left, uniprot_or_pdb_right, uniprot_sequence, pdb_sequence = self.align_cut(alignment, pdb_sequence_id)

            if uniprot_or_pdb_left == 'uniprot':
                cut_left_all_uniprot += cut_left
            elif uniprot_or_pdb_left == 'pdb':
                cut_left_all_pdb += cut_left
            if uniprot_or_pdb_right == 'uniprot':
                cut_right_all_uniprot += cut_right
            elif uniprot_or_pdb_right == 'pdb':
                cut_right_all_pdb += cut_right

            if cut:
                alignment, score, pdb_sequence.id = self.map_to_uniprot_helper(uniprot_sequence, pdb_sequence, saveAlignments)

        return alignment, score, [cut_left_all_uniprot, cut_right_all_uniprot], [cut_left_all_pdb, cut_right_all_pdb]
        
    
    
    def align_cut(self, alignment, pdb_sequence_id):
        """
        Checks for loners and shortens the sequence
        
        input:
        alignment               type class 'Bio.Align.MultipleSeqAlignment'
        pdb_sequence_id         type 'str'
        
        
        return:
        cut                     type 'bool'
        cut_left                type 'int'
        cut_right               type 'int'
        uniprot_or_pdb_left     type 'str'
        uniprot_or_pdb_right    type 'str'
        uniprot_sequence        type class 'Bio.SeqRecord.SeqRecord'
        pdb_sequence            type class 'Bio.SeqRecord.SeqRecord'
        """
        uniprot_alignment, pdb_alignment = self.pick_sequence(alignment, pdb_sequence_id)
        uniprot_sequence                 = self.get_sequence_from_alignment(uniprot_alignment)
        uniprot_sequence_old             = uniprot_sequence
        pdb_sequence                     = self.get_sequence_from_alignment(pdb_alignment)
        
        ## check for loners
        # left
        seq_left, uniprot_or_pdb_left   = self.check_for_loners(uniprot_alignment, pdb_alignment, 'left')
        do_shorten_left, loners_left    = self.check_loners(seq_left, 'left')
        # right
        seq_right, uniprot_or_pdb_right = self.check_for_loners(uniprot_alignment, pdb_alignment, 'right')
        do_shorten_right, loners_right  = self.check_loners(seq_right, 'right')

        
        cut = False
        cut_left = 0
        cut_right = 0
        # get the amount to cut left
        if do_shorten_left == True:
            cut = True
            seq_begin, seq_end, gap_end = loners_left
            # nr. of amino acids gone astray
            aa = seq_end - seq_begin
            # shorten by length of the gap minus 2 (or three to be genourous)
            # gap_end is the position where the first gap ends, thus the number
            # of amino acids that occured until that gap have to be taken into account
            cut_left = gap_end - aa
            assert( cut_left >= 0 )
        # get the amount to cut right
        if do_shorten_right == True:
            cut = True
            seq_begin, seq_end, gap_end = loners_right
            # nr. of amino acids gone astray
            aa = seq_begin - seq_end
            cut_right = (len(uniprot_alignment) - gap_end) - aa
            assert( cut_right >= 0 )
        

        # only shorten the uniprot sequence
        # Sebastian determined the domain boundaries. It is more reliable for
        # proteins with structure and the domain boundaries of the pdbs are
        # thus not modified. By uncommenting the bit below this could be changed.
        if cut:
            if cut_right == 0:
                if uniprot_or_pdb_right == 'uniprot' and uniprot_or_pdb_left == 'uniprot':
                    uniprot_sequence = uniprot_sequence[cut_left:]
                #elif uniprot_or_pdb_right == 'uniprot' and uniprot_or_pdb_left == 'pdb':
                #    pdb_sequence = pdb_sequence[cut_left:]
                elif uniprot_or_pdb_right == 'pdb' and uniprot_or_pdb_left == 'uniprot':
                    uniprot_sequence = uniprot_sequence[cut_left:]
                elif uniprot_or_pdb_right == 'pdb' and uniprot_or_pdb_left == 'pdb':
                    pass
                #    pdb_sequence = pdb_sequence[cut_left:]
                else:
                    print 'You must specify uniprot or pdb!'
                    print 'uniprot_or_pdb_right', uniprot_or_pdb_right
                    print 'uniprot_or_pdb_left', uniprot_or_pdb_left
            else:
                if uniprot_or_pdb_right == 'uniprot' and uniprot_or_pdb_left == 'uniprot':
                    uniprot_sequence = uniprot_sequence[cut_left:-cut_right]
                elif uniprot_or_pdb_right == 'uniprot' and uniprot_or_pdb_left == 'pdb':
                    uniprot_sequence = uniprot_sequence[:-cut_right]
                #    pdb_sequence = pdb_sequence[cut_left:]
                elif uniprot_or_pdb_right == 'pdb' and uniprot_or_pdb_left == 'uniprot':
                    uniprot_sequence = uniprot_sequence[cut_left:]
                #    pdb_sequence = pdb_sequence[:-cut_right]
                elif uniprot_or_pdb_right == 'pdb' and uniprot_or_pdb_left == 'pdb':
                #    pdb_sequence = pdb_sequence[cut_left:-cut_right]
                    pass
                else:
                    print 'You must specify uniprot or pdb!'
                    print 'uniprot_or_pdb_right', uniprot_or_pdb_right
                    print 'uniprot_or_pdb_left', uniprot_or_pdb_left
        
        # since only the uniprot sequence is shortend, but above it works in
        # principle for both sequences simultaniously, a endless while loop can occur
        # to avoid this, check if the uniprot sequence is cut or not.
        if len(uniprot_sequence_old.seq) == len(uniprot_sequence.seq):
            cut = False

        return cut, cut_left, cut_right, uniprot_or_pdb_left, uniprot_or_pdb_right, uniprot_sequence, pdb_sequence


    
    def pick_sequence(self, alignment, pdb_sequence_id):
        """
        Pick the uniprot and pdb sequences from the alignment
        
        input:
        alignment           type class 'Bio.Align.MultipleSeqAlignment'
        pdb_sequence_id     type 'str'
        
        return:
        uniprot_alignment   type class 'Bio.SeqRecord.SeqRecord'
        pdb_alignemnt       type class 'Bio.SeqRecord.SeqRecord'
        """
        for align in alignment:
            if align.id != pdb_sequence_id:
                uniprot_alignment = align
            else:
                pdb_alignemnt = align
        
        return uniprot_alignment, pdb_alignemnt

    
    def get_pdb_sequence(self, pdbCode, chain, domain_pdb):
        """
        Return the pdb file sequence (not SEQRES)
        
        input:
        pdbCode                 type 'str'
        chain                   type 'str'
        domain_pdb              type 'list' of 'int'
        
        result                  type class 'Bio.SeqRecord.SeqRecord'
        domain_pdb              type 'tuple' of 'int'
        chainNumberingDomain    type 'list' of 'int'
        """
        domains = [domain_pdb, ]
        pdb = pdbTemplate(self.pdbPath, pdbCode, chain, domains, self.tmpPath + self.unique)
        
        HETATMsInChain_PDBnumbering, HETflag, chains_pdb_order = pdb.extract()

        chainNumberingDomain = pdb.getChainNumberingNOHETATMS(chain)
        if chainNumberingDomain == []:
            raise error.pdbError('Could not get the pdb numbering for ' + pdbCode + '_' + chain)

        # it happend that the given domain boundaries are larger than the
        # chain found in the pdb file. In this case, set the boundaries to the
        # maximum of the pdb chain
        if domain_pdb[0] < chainNumberingDomain[0]:
            domain_pdb[0] = chainNumberingDomain[0]
        if domain_pdb[1] > chainNumberingDomain[-1]:
            domain_pdb[1] = chainNumberingDomain[-1]

        # translate the pdb_domain from pdb numbering to sequence numbering
        try:
            domain_pdb = chainNumberingDomain.index(domain_pdb[0])+1, chainNumberingDomain.index(domain_pdb[1])+1
        except ValueError:
            raise error.pdbError('ValueError when mapping domain boundaries to sequence numbering: ' + pdbCode + '_' + chain)


        pdb_sequence = next(SeqIO.parse(self.tmpPath + self.unique + pdbCode + chain + '.seq.txt', 'fasta'))
        return pdb_sequence, domain_pdb, chainNumberingDomain

    
#    def get_pdb_sequence(self, pdbCode, chain, domain_pdb):
#        """
#        Return the pdb file sequence (not SEQRES)
#        
#        input:
#        pdbCode                 type 'str'
#        chain                   type 'str'
#        domain_pdb              type 'list' of 'int'
#        
#        result                  type class 'Bio.SeqRecord.SeqRecord'
#        domain_pdb              type 'tuple' of 'int'
#        chainNumberingDomain    type 'list' of 'int'
#        """
#        domains = [domain_pdb, ]
#        pdb = pdbTemplate(self.pdbPath, pdbCode, chain, domains, self.tmpPath + self.unique)
#        
#        HETATMsInChain_PDBnumbering, HETflag, chains_pdb_order = pdb.extract()
#
#        chainNumberingDomain = pdb.getChainNumberingNOHETATMS(chain)
#        if chainNumberingDomain == []:
#            raise error.pdbError('Could not get the pdb numbering for ' + pdbCode + '_' + chain)
#
#        # it happend that the given domain boundaries are larger than the
#        # chain found in the pdb file. In this case, set the boundaries to the
#        # maximum of the pdb chain
#        if domain_pdb[0] < chainNumberingDomain[0]:
#            domain_pdb[0] = chainNumberingDomain[0]
#        if domain_pdb[1] > chainNumberingDomain[-1]:
#            domain_pdb[1] = chainNumberingDomain[-1]
#
#        try:
#            # Raise the first domain boundary if that AA does not exist
#            if chainNumberingDomain.count(domain_pdb[0]) != 1:
#                for chainNumber in chainNumberingDomain:
#                    if chainNumber > domain_pdb[0]:
#                        domain_pdb[0] = chainNumber
#                        break
#            # Lower the second domain boundary if that AA does not exist
#            if chainNumberingDomain.count(domain_pdb[1]) != 1:
#                for chainNumber in reversed(chainNumberingDomain):
#                    if chainNumber < domain_pdb[1]:
#                        domain_pdb[1] = chainNumber
#                        break
#            # Translate the pdb_domain from pdb numbering to sequence numbering                
#            domain_pdb = chainNumberingDomain.index(domain_pdb[0])+1, chainNumberingDomain.index(domain_pdb[1])+1
#        except ValueError:
#            print "PDB code, chain:", pdbCode, chain
#            print "Domains:", domains
#            print "Dobain_pdb 1/2:", domain_pdb[0], domain_pdb[1]
#            print "ChainNumberingDomain:"
#            print chainNumberingDomain            
#            raise error.pdbError('ValueError when mapping domain boundaries to sequence numbering: ' + pdbCode + '_' + chain)
#
#        pdb_sequence = next(SeqIO.parse(self.tmpPath + self.unique + pdbCode + chain + '.seq.txt', 'fasta'))
#        return pdb_sequence, domain_pdb, chainNumberingDomain    
    
    
    def get_identity(self, alignment):
        """
        Return the sequence identity of two aligned sequences
        It takes the longer sequence as the reference
        takes a biopython alignment object as input. make sure that the alignment
        has only two sequences
        
        input
        alignment       type class 'Bio.Align.MultipleSeqAlignment'
        
        return:
                        type float
        """
        assert( len(alignment) == 2 )
        
        length_seq1 = len(alignment[0].seq.tostring().replace('-', ''))
        length_seq2 = len(alignment[1].seq.tostring().replace('-', ''))
        
        j = 0 # counts positions in first sequence
        i = 0 # counts identity hits
    
        if length_seq1 <= length_seq2:
            for amino_acid in alignment[0].seq:
                if amino_acid == '-':
                    pass
                else:
                    if amino_acid == alignment[1].seq[j]:
                        i += 1
                j += 1
        else:
            for amino_acid in alignment[1].seq:
                if amino_acid == '-':
                    pass
                else:
                    if amino_acid == alignment[0].seq[j]:
                        i += 1
                j += 1
        
        return float(100*i/min(length_seq1, length_seq2))
    
    
    def get_coverage(self, alignment):
        """
        Returns the coverage of the alginment in % 
        
        input
        alignment       type class 'Bio.Align.MultipleSeqAlignment'>
        """
        assert( len(alignment) == 2 )
        length_seq1 = len(alignment[0].seq.tostring().replace('-', ''))
        length_seq2 = len(alignment[1].seq.tostring().replace('-', ''))
        
        if length_seq1 >= length_seq2:
            return 100.0 * float(length_seq2) / float(length_seq1)
        else:
            return 100.0 * float(length_seq1) / float(length_seq2)
    
    

    #
    # ends here
    ###########

    ###########
    # for map_to_pdb_sequence
    #
    def map_to_pdb_sequence(self, alignment, alignmentID, position):
        """
        Given an alignment and a position of the uniprot sequence, this function
        maps the position of the uniprot sequence to the pdb sequence
        !! Note that the position numbering start with 1 !!
        
        input
        alignment       type class 'Bio.Align.MultipleSeqAlignment'
        alignmentID     type 'str'
        position        type 'int'
        
        
        pdb_position    type 'int'

        """
        if alignment[0].id == alignmentID:
            alignment_protein = alignment[0]
            alignment_uniprot = alignment[1]
        elif alignment[1].id == alignmentID:
            alignment_protein = alignment[1]
            alignment_uniprot = alignment[0]
        else:
            print 'Could not assign the alignment to pdb and uniprot correctly!'
            return 1

        # now get the position
        pdb_position = 0
        uniprot_position = 0
        for index in range(len(alignment_uniprot)):
            if uniprot_position >= int(position)-1 and not alignment_uniprot[index] == '-':
                check = index
                break
            elif alignment_uniprot[index] == '-':
                pdb_position += 1
                continue
            elif alignment_protein[index] == '-':
                uniprot_position += 1
                continue
            else:
                pdb_position += 1
                uniprot_position += 1
        
        # check if the uniprot position falls into a gap
        if alignment_protein[check] == '-':
            return 'in gap'
        else:
            return pdb_position + 1


    #
    # ends here
    ###########
    
    #
    # for checking the alignment
    #########
    

    def check_loners(self, aligned_sequence, left_or_right):
        """
        Check if there are amino acids moved strangely far away from the central block
        
        check_loners
        aligned_sequence    type class 'Bio.SeqRecord.SeqRecord'
        left_or_right       type 'str'

        """
        amino_acid = 'RHKDESTNQCGPAVILMFYW'
        FIRST = True
        AMINO_ACID_START = False
        GAP_STARTED = False
        NO_GAP = True
        seq_begin = 0
        seq_end = 0
        gap_end = 0
        if left_or_right == 'left':
            indexes = range(len(aligned_sequence))
        elif left_or_right == 'right':
            indexes = range(len(aligned_sequence)-1,-1,-1)
        else:
            print 'You must specify left or right!'
        for i in indexes:
            if aligned_sequence[i] == '-' and FIRST:
                continue
            elif aligned_sequence[i] in amino_acid and FIRST:
                FIRST = False
                AMINO_ACID_START = True
                seq_begin = i
            elif aligned_sequence[i] == '-' and AMINO_ACID_START:
                loners_distance = 1
                AMINO_ACID_START = False
                GAP_STARTED = True
                seq_end = i
            elif aligned_sequence[i] in amino_acid and GAP_STARTED:
                gap_end = i
                NO_GAP = False
                break
            else:
                pass
        
        if NO_GAP:
            return False, []
            
        loners          = seq_end - seq_begin
        loners_distance = gap_end - seq_end
        

        if fabs(loners_distance) > fabs(loners):
            return True, [seq_begin, seq_end, gap_end]
        elif fabs(loners) / fabs(loners_distance) <= 0.2:
            return True, [seq_begin, seq_end, gap_end]
        else:
            return False, []


        
    
    
class get_template_core(get_template):
    """ retrieve the info from Sebastians file and do the alignment

    """
    
    def __init__(self, tmpPath, unique, pdbPath, savePDB, saveAlignments, 
                 pool, semaphore, get_uniprot_seq, core_template_database, 
                 get_resolution, log):
        """
        input
        tmpPath                     type 'str'
        unique                      type 'str'
        pdbPath                     type 'str'
        savePDB                     type 'str'
        saveAlignments              type 'str'  
        pool                        type class '__main__.ActivePool'
        semaphore                   type class 'multiprocessing.synchronize.Semaphore'
        get_uniprot_seq             <__main__.getUniprotSequence instance>
        core_template_database      <__main__.core_Templates instance>
        """
        # call the __init__ from the parent class
        get_template.__init__(self, tmpPath, unique, pdbPath, savePDB, saveAlignments,
                              pool, semaphore, get_uniprot_seq, get_resolution, log)
        
        # set the core database
        self.core_template_database = core_template_database



    def __call__(self, uniprotID1, mutation):
        """
        input:
        uniprotKB       type 'str'
        mutation        type 'str'
        
        return:
        pdbCode                             type 'str'
        chain                               type 'str'
        domain_pdb                          type 'list' of 'int'
        score                               type 'float'
        alignment                           type class 'Bio.Align.MultipleSeqAlignment'
        str(mutation_pdb)                   type 'str'
        uniprot_sequence_domain             type class 'Bio.SeqRecord.SeqRecord'
        mutation_position_domain_uniprot    type 'int'
        """
        # get the templates from Sebastians file
        core_templates = self.core_template_database(uniprotID1)

        if core_templates == []:
            return 'no template', []
        
        templates = []
        new_sequences = set()
        for core_template in core_templates:
            # mutation should be like A100T, template[2] is a list with amino acids
            # that are in the core
            # for now take mutations when they fall into the domain
            
            # if mutation not in core
            #if not int(mutation[1:-1]) in template[2]:
            # if mutation not in domain
            if not int(mutation[1:-1]) in range(core_template[1][0], core_template[1][1]):
                continue
            
            pfamID1         = core_template[0]
            domain_uniprot  = core_template[1]
            pdbCode        = core_template[3]
            chain_pdb        = core_template[4]
            domain_pdb     = core_template[5]
            
            uniprot_sequence, new_sequence = self.get_uniprot_seq(uniprotID1)
            if uniprot_sequence == 'no sequence':
                    continue

            uniprot_sequence_domain = self.make_SeqRec_object(uniprot_sequence, domain_uniprot, uniprotID1)
            
            result_tmp = self.map_to_uniprot(uniprotID1, uniprot_sequence, domain_uniprot, pdbCode, chain_pdb, domain_pdb, self.saveAlignments, refine=True)
            if result_tmp == 'error':
                continue
            else:
                alignment, score, pdb_sequence_id, domain_uniprot = result_tmp
    
            mutation_position_domain_uniprot = int(mutation[1:-1]) - domain_uniprot[0] + 1 # +1 to have the numbering staring with 1
            
            # map mutation to the aligned pdb sequence. This is done to make
            # sure that the mutation does not fall into a region which is not
            # covered by the pdb file.
            mutation_pdb = self.map_to_pdb_sequence(alignment, pdb_sequence_id, mutation_position_domain_uniprot)
            if mutation_pdb == 'in gap':
                continue
            
            # in case the domain boundaries of the uniprot sequence changed,
            # get the new sequence
            uniprot_sequence_domain = self.make_SeqRec_object(uniprot_sequence, domain_uniprot, uniprotID1)
    
            pdb_type, pdb_resolution = self.get_resolution(pdbCode)
                            
            template = {'uniprotIDs': (uniprotID1, ''),
                'pfamIDs'   : (pfamID1, ''),
                'domain_defs':(domain_uniprot, []),
                'mutation'  : mutation,
                'pdbID'     : pdbCode,
                'chains_pdb' : [chain_pdb[0], ],
                'pdb_domain_defs' : [domain_pdb, []],
                'mutation_position_domain' : mutation_position_domain_uniprot,
                'mutation_pdb': mutation_pdb,
                'pdb_type': pdb_type,
                'pdb_resolution' : pdb_resolution,
                'uniprot_domain_sequences' : [uniprot_sequence_domain, ''],
                'alignments' : [alignment, ],
                'alignment_scores' : [score, score, 0]}
            
            templates.append(template)
            
            if new_sequence:
                new_sequences.add((uniprotID1, uniprot_sequence))               

#       return (pdbCode, chain, domain_pdb, score, alignment, str(mutation_pdb), uniprot_sequence_domain, mutation_position_domain_uniprot, pfamID1, domain_uniprot), [[uniprotID1, uniprot_sequence], ]
        return templates, new_sequences


class get_template_interface(get_template):
    """
    Check if a mutation falls into an interface and tries to find the best
    structural template
    
    """
    def __init__(self, tmpPath, unique, pdbPath, savePDB, saveAlignments, pool, 
                 semaphore, get_uniprot_seq, get_interactions, get_3did_entries, 
                 get_resolution, include_all_pfam_interactions, log):
        """
        input
        
        tmpPath             type 'str'
        unique              type 'str'
        pdbPath             type 'str'
        savePDB             type 'str'
        saveAlignments      type 'str'
        pool                type class '__main__.ActivePool'
        semaphore           type class 'multiprocessing.synchronize.Semaphore'
        get_uniprot_seq     <__main__.getUniprotSequence instance>
        get_interactions    <__main__.getInteractions instance>
        get_3did_entries    <__main__.get3DID instance>
        get_resolution      <__main__.pdb_resolution instance>
        """
        # call the __init__ from the parent class
        get_template.__init__(self, tmpPath, unique, pdbPath, savePDB, saveAlignments,
                              pool, semaphore, get_uniprot_seq, get_resolution, log)
        
        # AS to output all pfam pairs
        self.include_all_pfam_interactions = include_all_pfam_interactions
        
        # set the databases
        self.get_3did_entries = get_3did_entries
        self.get_interactions = get_interactions
    
    
    def __call__(self, uniprotID1, mutation):
        """
        if no template is found: returns a dictionary that has a has_key('errors')  'no template found'
        otherwise returns a dictionary with keys:
            pdbCode: of the template found
            chain1: chains to be used as template 
            chain2: 
            score1: sequence identity with chain 1
            score2: seq, id. with chain 2
            pfam family of interaction partner 1 (i.e. the query uniprot), 
            pfam family of the interaction partner 2 (from Sebastians file)
            uniprotID2: of the second interaction partner
            uniprotID1_sequence1_domain: uniprot sequence for the domain only
            uniprotID2_sequence2_domain:
            alignment1: biopython alignment obejct with the alignment of uniprot seq1 with chain1
            alignment2:
            mutation_position_domain: mutation position in the domain (shortened pdb sequence)
            int: 0 means X-ray, 2 NMR, 3 other
            float: resolution of the structure
            
        input:
        uniprotID1   type 'str'
        mutation    type 'str'
        
        return
                    type 'dict'
                    
                    entries of one element of the list (same for the run() method):
                        type        description
                        'str'       pdbCode: of the template found
                        'str'       chain1: chains to be used as template 
                        'str'       chain2: 
                        'float'     score: based on sequence identity and coverage
                        'float'     score1: score of chain 1
                        'float'     score2: score of chain 2
                        'str'       pfam family of interaction partner 1 (i.e. the query uniprot), 
                        'str'       pfam family of the interaction partner 2 (from Sebastians file)
                        'str'       uniprotID1_2: of the second interaction partner
                        'Bio.SeqRecord.SeqRecord'           uniprotID1_sequence1_domain: uniprot sequence for the domain only
                        'Bio.SeqRecord.SeqRecord'           uniprotID2_sequence2_domain:
                        'Bio.Align.MultipleSeqAlignment'    alignment1: biopython alignment obejct with the alignment of uniprot seq1 with chain1
                        'Bio.Align.MultipleSeqAlignment'    alignment2:
                        'int'       mutation_position_domain: mutation position in the domain (shortened pdb sequence)
                        'str'       pdb_domain1, looks like '74-390'
                        'str'       pdb_domain2, looks like '74-390'
                        'int'       exp. measurement method; 0 means X-ray, 2 NMR, 3 other
                        'float'     resolution of the structure
        """
        # get all possible templates
        templates, new_sequences = self.run(uniprotID1, mutation)
        
        self.log.info("Done getting interface templates...")
#        self.log.debug("Templates:")
#        self.log.debug(templates)
        
        if (templates == []) or (templates == [[]]) or (templates == [[[]]]):
            return [[]], new_sequences
        else:
            # select the best template
            best_templates = self.chose_best_template(templates)
#            self.log.debug("Best templates:")
#            self.log.debug(best_templates)
            
            best_templates_refined = []
            for template in best_templates:
                # Refine the best template, i.e. check for errors in the alignment
                # and realign
                template_refined, no_longer_new_sequences = self.run(uniprotID1, mutation, template)
                best_templates_refined.append(template_refined[0][0])
            
            self.log.info('Done refining interface templates...')
#            self.log.debug("Best templates refined:")
#            self.log.debug(best_templates_refined)
            
            return best_templates_refined, new_sequences
        
    
    def run(self, uniprotID1, mutation, SELECT_ONLY=[]):
        """
        Look up all interactions for a given uniprotID1, check if the mutation
        falls into the interface and select a template
        
        input:
        uniprotID1       type 'str'
        mutation        type 'str'       ; Q61L
        
        return:
            see __call__ method
        """
    
        templates = []
        template_clans = set()
        
        new1 = False
        new2 = False
        
        # SELECT_ONLY is used in the refinement step to select only the interaction
        # and the pdb file which was identified as best template in the first
        # iteration
        if SELECT_ONLY == []:
            refine = False
        else:
            refine = True
            select_pdbCode       = SELECT_ONLY['pdbID']
            select_chain1        = SELECT_ONLY['chains_pdb'][0]
            select_chain2        = SELECT_ONLY['chains_pdb'][1]
            select_Pfam_1        = SELECT_ONLY['pfamIDs'][0]
            select_Pfam_2        = SELECT_ONLY['pfamIDs'][1]
            select_uniprotID2   = SELECT_ONLY['uniprotIDs'][1]

        interactions = self.get_interactions(uniprotID1)
        # interaction is a list: [firstGuy, interaction_type_firstGuy, PfamID_firstGuy, domain, interface, \
        #                         secondGuy, interaction_type_secondGuy, PfamID_secondGuy, domain2
        
        if interactions == []:
            return [], []
        

        for interaction in interactions:
            # for the refinement of the alignment skip the wrong interactions
            if refine and interaction.uniprotIDs[1] != select_uniprotID2:
                continue
            if refine and interaction.pfamIDs[0] != select_Pfam_1:
                continue
            if refine and interaction.pfamIDs[1] != select_Pfam_2:
                continue
            
            # if you are testing:
            # uncomment the following. There are many! Pkinase interactions and
            # it takes ages to go through all of them. Better find another example
#            if interaction[7] == 'Pkinase_Tyr' or interaction[2] == 'Pkinase_Tyr':
            
            # check if the mutation falls into the interface
#            if interaction.interface == 'NULL' or interaction.interface == '':
#                continue
#            AS commented out the following two lines because errors in Sabastian's interface file 
#                may be preventing interfaces from being detected
#            elif int(mutation[1:-1]) not in [ int(x) for x in interaction[4].split(',') ]:
#                continue
            if False:
                continue
            
            # skip ELM interactions. This should probably be included in future
            # versions            
            if interaction.interaction_type == 'ELM':
                continue
            
            pdbs = self.get_3did_entries(*interaction.pfamIDs)
            
            self.log.info("Going over every interaction reported in the database for a given uniprot...")
            self.log.debug("uniprotID1: " + interaction.uniprotIDs[0] + ':' + interaction.uniprotIDs[1])
            self.log.debug("Interactions: " + interaction.pfamIDs[0] + ':' + interaction.pfamIDs[1])
            
            if pdbs == 'no entry':
                continue

            for pdb in pdbs:
                # get_3did_entries returns all the pdbs that are listed as
                # having the two domains, 'pdb' is a list [pdbCode, chain1, chain2]
                pdbCode, chain_pdb1, chain_pdb2, pdb_domain1, pdb_domain2 = pdb
                
                # there are some obsolete pdbs, ignore them
                # or 2NP8 has only one chain
                if pdbCode in ['3C4D', '3LB7', '3NSV', '2NP8', '2WN0']:
                    continue
                    
                # for the refinement of the alignment skip if it is not the correct pdb:
                if refine and pdbCode != select_pdbCode:
                    continue
                if refine and chain_pdb1 != select_chain1:
                    continue
                if refine and chain_pdb2 != select_chain2:
                    continue
                
                uniprotID2 = interaction.uniprotIDs[1]
                
                # first interaction partner
                uniprot_domain1 = interaction.domain_defs[0]
                # if the mutation does not fall into the domain, skip
                if int(mutation[1:-1]) not in range(uniprot_domain1[0], uniprot_domain1[1]+1):
                    continue
                # probably check here if the mutation falls into the interface
                # currently I am not sure if the interface information is accurate
                uniprot_sequence1, new1 = self.get_uniprot_seq(uniprotID1)
                if uniprot_sequence1 == 'no sequence':
                    continue
                
                # second interaction partner
                uniprot_domain2 = interaction.domain_defs[1]
                uniprot_sequence2, new2 = self.get_uniprot_seq(uniprotID2)
                if uniprot_sequence2 == 'no sequence':
                    continue

                alignment1, score1, alignmentID1, uniprot_domain1 = \
                self.map_to_uniprot(uniprotID1, uniprot_sequence1, uniprot_domain1, pdbCode, chain_pdb1, pdb_domain1, self.saveAlignments, refine)

                alignment2, score2, alignmentID2, uniprot_domain2 = \
                self.map_to_uniprot(uniprotID2, uniprot_sequence2, uniprot_domain2, pdbCode, chain_pdb2, pdb_domain2, self.saveAlignments, refine)
                
                score = float(score1) + float(score2)

                # mutation numbered from the beginning of uniprot domain, rather than the beginning of uniprot
                mutation_position_domain = int(mutation[1:-1]) - uniprot_domain1[0] + 1 # +1 to have the numbering staring with 1

                # cut sequence to boundaries and set sequence ID
                uniprot_sequence1_domain = self.make_SeqRec_object(uniprot_sequence1, uniprot_domain1, uniprotID1)
                uniprot_sequence2_domain = self.make_SeqRec_object(uniprot_sequence2, uniprot_domain2, uniprotID1)
                
                # map mutations to PDB
                mutation_pdb1 = self.map_to_pdb_sequence(alignment1, alignmentID1, mutation_position_domain)

                if mutation_pdb1 == 'in gap':
                    continue
                contacts_chain1 = self.check_structure(pdbCode, chain_pdb1, chain_pdb1 + '_' + mutation[0] + str(mutation_pdb1) + mutation[-1])

                pdb_type, pdb_resolution = self.get_resolution(pdbCode)
                                          
                if contacts_chain1[chain_pdb2]:      
                    template = {'uniprotIDs': (uniprotID1, uniprotID2,),
                                'pfamIDs'   : (interaction.pfamIDs[0], interaction.pfamIDs[1],),
                                'domain_defs':(tuple(uniprot_domain1), tuple(uniprot_domain2),),
                                'mutation'  : mutation,
                                'pdbID'     : pdbCode,
                                'chains_pdb' : [chain_pdb1, chain_pdb2,],
                                'pdb_domain_defs' : (tuple(pdb_domain1), tuple(pdb_domain2),),
                                'mutation_position_domain' : mutation_position_domain,
                                'mutation_pdb': mutation_pdb1,
                                'pdb_type': pdb_type,
                                'pdb_resolution' : pdb_resolution,
                                'uniprot_domain_sequences' : (uniprot_sequence1_domain, uniprot_sequence2_domain,), 
                                'alignments' : (alignment1, alignment2,),
                                'alignment_scores' : (score, float(score1), float(score2),)}
                                            
                    templates.append(template)
                    template_clans.add((template['uniprotIDs'], template['pfamIDs'], template['domain_defs'],))

                                        
        new_sequences = list()
        if new1:
            new_sequences.append([uniprotID1, uniprot_sequence1])
        if new2:
            new_sequences.append([uniprotID2, uniprot_sequence2])

        # Select the best template for each unique interaction pattern    
        template_clan_templates = []
        for template_clan in template_clans:
            template_clan_template = []
            for template in templates:
                if ((template['uniprotIDs'], template['pfamIDs'], template['domain_defs'],)) == template_clan:
                    template_clan_template.append(template)
            template_clan_templates.append(template_clan_template)        

        return template_clan_templates, new_sequences

     

    def chose_best_template(self, template_clan_templates):
        """
        Selects the best template based on sequence identity and resolution
        of the pdb structure
        
        input:
        templates       type list
        
        return:
        compare __call__() method
        """

        best_templates = list()
        for template_clans in template_clan_templates:
            # first sort by identity score:
            templates_sorted = sorted(template_clans, key=lambda k: k['alignment_scores'][0], reverse=True)
            max_score = templates_sorted[0]['alignment_scores']
            templates_highest_identity = list()
            for template in templates_sorted:
                if template['alignment_scores'] == max_score:
                    templates_highest_identity.append(template)
            
            # next, sort by pdb resolution
            templates_highest_identity = sorted(templates_highest_identity, key=lambda k: (k['pdb_type'], k['pdb_resolution'],), reverse=False)
            
            # return the firt template in the list, i.e. the best template
            best_templates.append(templates_highest_identity[0])
            
        return best_templates


    ###########
    # for check_structure
    #
    def check_structure(self, pdbCode, chainID, mutation):
        """ checks if the mutation falls into the interface, i.e. is in contact with
        another chain
        'mutation' has to be of the form A_T70H, mutation in chain A, from Tyr at
        position 70 to His
        NOTE: takes the mutation as numbered ins sequence! The conversion is done
        within this function!
        
        input
        pdbCode     type 'str'
        chainID     type 'str'
        mutation    type 'str'      ; B_Q61L
        
        return:
        contacts    type 'dict'     ; {'C': False, 'B': True}
                                      key:   chainID                type 'str'
                                      value: contact to chainID     type boolean
        """
        structure = self.getPDB(pdbCode, self.pdbPath)
        model = structure[0]
    
        chains   = [ chain for chain in model]
        chainIDs = [ chain.id for chain in model]
    
        fromAA = mutation[2]
        position = self.convert_mutation_position(model, mutation) # convert the position numbering
        contacts = { chainID: False for chainID in chainIDs if not chainID == mutation[0] }
        
        for i in range(len(chains)):
            if chains[i].id == mutation[0]:
                chain = chains[i]
                # use list expansion to select only the 'opposing chains'
                oppositeChains = [ x for x in chains if x != chains[i] ]
        
        # If the residues do not match, issue a warning.
        # To obtain a better model one could restrict to templates that have
        # the same amino acid as the uniprot sequence at the position of the mutation.
#        if chain[position].resname != self.convert_aa(fromAA):
#            print 'Residue missmatch while checking the structure!'
#            print 'pdbCode', pdbCode
#            print 'mutation', mutation
#            print chain[position].resname, self.convert_aa(fromAA)
#            print 'position', position

       
        for oppositeChain in oppositeChains:
            # check each residue
            for residue in oppositeChain:
                # for each residue each atom of the mutated residue has to be checked
                for atom1 in chain[position]: # chain[position] is the residue that should be mutated
                    # and each atom
                    for atom2 in residue:
                        r = self.distance(atom1, atom2)
                        if r <= 5.0:
                            contacts[oppositeChain.id] = True

        return contacts


    def convert_mutation_position(self, model, mutation):
        """ maps the mutation sequence position of the pdb to pdb numbering
        
        input
        model       class 'Bio.PDB.Model.Model'
        mutation    type 'str'                      ; B_Q61L
        
        return:
        chainNumbering[position-1]      type 'int'
        """
        chain = model[mutation[0]]
        position = int(mutation[3:-1])
        
        chainNumbering = self.getChainNumberingNOHETATMS(chain)

        return chainNumbering[position-1]
    
    
    def getChainNumberingNOHETATMS(self, chain):
        """
        returns a list with the numbering of the chains
        
        input:
        chain               class 'Bio.PDB.Chain.Chain'
        
        return:
        chainNumbering      type 'list' of 'int'
        """
        chainNumbering = list()
        amino_acids = ['ARG', 'HIS', 'LYS', 'ASP', 'GLU', 'SER', 'THR', 'ASN', 'GLN', 'CYS', 'GLY', 'PRO', 'ALA', 'VAL', 'ILE', 'LEU', 'MET', 'PHE', 'TYR', 'TRP']
        for residue in chain:
            if residue.resname in amino_acids and residue.id[0] == ' ':
                chainNumbering.append(residue.id[1])

#        chainNumbering = [residue.id[1] for residue in chain if is_aa(residue, standard=True)]
        return chainNumbering
    
    
    def getPDB(self, pdbCode, pdbPath):
        """
        parse a pdb file with biopythons PDBParser() and return the structure
        
        input: pdbCode  type String     four letter code of the PDB file
        
        return: Biopython pdb structure
        
        input:
        pdbCode     type 'str'
        pdbPath     type 'str'
        
        return:
        result      type class 'Bio.PDB.Structure.Structure'
        """
        parser = PDBParser(QUIET=True) # set QUIET to False to output warnings like incomplete chains etc.
        pdbFile = pdbPath + pdbCode[1:3].lower() + '/pdb' + pdbCode.lower() + '.ent.gz'
        pdbFileUncompressed = gzip.open(pdbFile, 'r')
        result = parser.get_structure('ID', pdbFileUncompressed)

        return result
    
     
    def distance(self, atom1, atom2):
        """
        returns the distance of two points in three dimensional space
        
        input: atom instance of biopython: class 'Bio.PDB.Atom.Atom
        
        return:
                type 'float'
        """
        a = atom1.coord
        b = atom2.coord
        assert(len(a) == 3 and len(b) == 3)
        return sqrt(sum( (a - b)**2 for a, b in zip(a, b)))
    
    
    def convert_aa(self, aa):
        """
        input:
        aa      type 'str'
        
        return:
                type 'str'
        """
        A_DICT = {'A':'ALA', 'R':'ARG', 'N':'ASN', 'D':'ASP', 'C':'CYS', 'E':'GLU', \
                  'Q':'GLN', 'G':'GLY', 'H':'HIS', 'I':'ILE', 'L':'LEU', 'K':'LYS', \
                  'M':'MET', 'F':'PHE', 'P':'PRO', 'S':'SER', 'T':'THR', 'W':'TRP', \
                  'Y':'TYR', 'V':'VAL', 'U':'SEC', 'O':'PYL', \
                  'B':'ASX', 'Z':'GLX', 'J':'XLE', 'X':'XAA', '*':'TER'}
        
        AAA_DICT = dict([(value,key) for key,value in A_DICT.items()])
        
        if len(aa) == 3:
            try:
                return AAA_DICT[aa.upper()]
            except KeyError:
                print  'Not a valid amino acid'
                return
        if len(aa) == 1:
            try:
                return A_DICT[aa.upper()]
            except KeyError:
                print  'Not a valid amino acid'
                return
        print 'Not a valid amino acid'
    #
    # ends here
    ###########

if __name__ == '__main__':
    
    from pipeline import ActivePool
    from pipeline import getUniprotSequence
    import multiprocessing
    from Bio import AlignIO
    
    get_uniprot_seq = getUniprotSequence('doesntmatter')
    pool = ActivePool()
    semaphore = multiprocessing.Semaphore(2)
    
    
    tmpPath = '/tmp/test/'
    unique = 'unique'
    pdbPath = '/home/niklas/pdb_database/structures/divided/pdb/'
    savePDB = '/tmp/test/trash/'
    saveAlignments = '/tmp/test/alignments/'
    
    
    a = get_template(tmpPath, unique, pdbPath, savePDB, saveAlignments, pool, semaphore, get_uniprot_seq)

    alignment = AlignIO.read('/home/niklas/tmp/alignment_cluttered.fasta', 'fasta')
#    print alignment
    score = '100'
    pdb_sequence_id = '1LFD'
    
    alignment, score = a.align_shorten(alignment, score, pdb_sequence_id, saveAlignments)
    
#    print alignment