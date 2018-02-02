
import pandas as pd
import networkx as nx
import numpy as np
import scipy.stats
from collections import OrderedDict
if __name__ == 'subroutines.OPM':
    from subroutines.run_stages import run_stages
else:
    from datagen.subroutines.run_stages import run_stages

class extract_strand_tilt_and_TM_regions(run_stages):

    def __init__(self, run_parameters):
        run_stages.__init__(self, run_parameters)

    def parse_opm(self, orig_dir):
        # Extracts strand tilt and TM information from the OPM database
        # (docs/OPM_TM_subunits.txt)
        pdb_codes = []
        chains = []
        tilt_angles = []
        tm_lists = []
        tm_segment_lists = []
        with open('{}/docs/OPM_TM_subunits.txt'.format(orig_dir), 'r') as opm_file:
            for line in opm_file:
                line_segments = line.split('-')
                pdb_codes.append(line_segments[0][0:4])
                chain = line_segments[0][4:].strip()
                chains.append(chain)
                tilt_angle = line_segments[1].replace('Tilt:', '')
                tilt_angle = tilt_angle.replace('°', '')
                tilt_angles.append(tilt_angle.strip())
                tm_segments = '-'.join(line_segments[2:])
                tm_segments = tm_segments.replace('Segments:', '')
                tm_segments = tm_segments.split(',')
                tm_segment_lists.append(tm_segments)
                tm_residues = []
                for segment in tm_segments:
                    tm_range = ''
                    start = False
                    stop = False
                    for char in list(segment):
                        if char == ')':
                            stop = True

                        if start is True and stop is False:
                            tm_range += char

                        if char == '(':
                            start = True

                    res_min = int(tm_range.split('-')[0])
                    res_max = int(tm_range.split('-')[1])
                    tm_residues = tm_residues + [chain+str(num) for num in
                                                 range(res_min, res_max+1)]
                tm_lists.append(tm_residues)

        opm_df = pd.DataFrame({'PDB_CODE': pdb_codes,
                               'CHAIN': chains,
                               'TILT_ANGLE': tilt_angles,
                               'TM_RANGE': tm_lists,
                               'SEGMENTS': tm_segment_lists})

        return opm_df

    def find_strand_tilt(self, sec_struct_dfs_dict, opm_df):
        # Determines strand tilt
        pdb_codes_list = opm_df['PDB_CODE'].tolist()
        tilt_angles = OrderedDict()

        for domain_id in list(sec_struct_dfs_dict.keys()):
            pdb_code = domain_id[0:4]

            if pdb_code in pdb_codes_list:
                index = pdb_codes_list.index(pdb_code)
                tilt_angle = opm_df['TILT_ANGLE'][index]
                tilt_angles[domain_id] = tilt_angle

            else:
                tilt_angles[domain_id] = 'Undefined'

        return tilt_angles


class calculate_barrel_geometry(run_stages):

    def __init__(self, run_parameters):
        run_stages.__init__(self, run_parameters)

    def find_barrel_strand_number(self, sec_struct_dfs_dict):
        strand_numbers = OrderedDict()

        for domain_id, sec_struct_df in sec_struct_dfs_dict.items():
            strands = [int(strand) for strand in
                       set(sec_struct_df['STRAND_NUM'].tolist()) if strand != '']
            strand_count = max(strands)
            strand_numbers[domain_id] = strand_count

        return strand_numbers

    def find_barrel_shear_number(self, sec_struct_dfs_dict, domain_sheets_dict):
        unprocessed_list = []
        shear_numbers = OrderedDict()

        for domain_id, sec_struct_df in sec_struct_dfs_dict.items():
            networks = [network for key, network in domain_sheets_dict.items()
                        if domain_id in key]
            if len(networks) > 1:
                print('ERROR: More than one beta-sheet retained for {} '
                      'barrel'.format(domain_id))
            G = networks[0]

            nodes_dict = {}
            strands = nx.nodes(G)
            for strand in strands:
                nodes_dict[strand] = len(G.neighbors(strand))
            try:
                while min(list(nodes_dict.values())) < 2:
                    for strand in strands:
                        if len(G.neighbors(strand)) < 2:
                            G.remove_node(strand)
                            del nodes_dict[strand]
                    strands = nx.nodes(G)
                    for strand in strands:
                        nodes_dict[strand] = len(G.neighbors(strand))
            except ValueError:
                unprocessed_list.append(domain_id)
                continue

            cycles = [strand for cycle in nx.cycle_basis(G) for strand in cycle]
            if len(set(cycles)) != len(nx.nodes(G)):
                unprocessed_list.append(domain_id)
                continue

            # WORKS UP TO HERE
            strands = nx.cycle_basis(G)[0]  # Finds first complete cycle
            res_array = np.zeros((len(strands)+1, 1000))

            processed_strands = []
            strand_1 = strands[0]
            processed_strands.append(strand_1)
            strand_1_df = sec_struct_df[sec_struct_df['STRAND_NUM']==strand_1]
            dssp_num = strand_1_df['DSSP_NUM'].tolist()
            for index, res in enumerate(dssp_num):
                res_array[0, 400+index] = res
            res_list_1 = res_array[0:1,].tolist()
            res_list_1 = [res for res_sub_list in res_list_1 for res in res_sub_list]
            res_list = res_array[0:1,].tolist()
            res_list = [res for res_sub_list in res_list for res in res_sub_list]

            current_strand = strand_1
            count = 0
            while any(x not in processed_strands for x in G.neighbors(current_strand)):
                next_strand = G.neighbors(current_strand)[0]
                if next_strand in processed_strands:
                    next_strand = G.neighbors(current_strand)[1]
                processed_strands.append(next_strand)
                count = count + 1

                next_strand_df = sec_struct_df[sec_struct_df['STRAND_NUM']==next_strand]
                dssp_num = next_strand_df['DSSP_NUM'].tolist()
                h_bonds = next_strand_df['H-BONDS'].tolist()
                orientations = next_strand_df['ORIENTATION'].tolist()
                pair_index = ''
                for h_bonds_index, pair in enumerate(h_bonds):
                    if float(pair[0]) != 0.0 and float(pair[0]) in res_list:
                        pair_index = 0
                    elif float(pair[1]) != 0.0 and float(pair[1]) in res_list:
                        pair_index = 1
                    else:
                        continue
                h_bonds = [pair[pair_index] for pair in h_bonds]
                orientations = [pair[pair_index] for pair in orientations]
                if set([orientation for orientation in orientations if orientation != '']) == {'A'}:
                    h_bonds.reverse()
                elif set([orientation for orientation in orientations if orientation != '']) != {'P'}:
                    print('ERROR: Strand {} is listed as both antiparallel and '
                          'parallel to strand {}'.format(next_strand, current_strand))
                for h_bonds_index, res in enumerate(h_bonds):
                    if float(res) != 0.0 and float(res) in res_list:
                        res_list_index = res_list.index(float(res))
                        break
                index_diff = abs(res_list_index - h_bonds_index)
                for h_bonds_index, res in enumerate(h_bonds):
                    res_array[count, h_bonds_index+index_diff] = dssp_num[h_bonds_index]
                res_list = res_array[count:count+1,].tolist()
                res_list = [res for res_sub_list in res_list for res in res_sub_list]

                current_strand = next_strand

            strand_1_df = sec_struct_df[sec_struct_df['STRAND_NUM']==strand_1]
            dssp_num = strand_1_df['DSSP_NUM'].tolist()
            h_bonds = strand_1_df['H-BONDS'].tolist()
            orientations = strand_1_df['ORIENTATION'].tolist()
            pair_index = ''
            for h_bonds_index, pair in enumerate(h_bonds):
                if float(pair[0]) != 0.0 and float(pair[0]) in res_list:
                    pair_index = 0
                elif float(pair[1]) != 0.0 and float(pair[1]) in res_list:
                    pair_index = 1
                else:
                    continue
            h_bonds = [pair[pair_index] for pair in h_bonds]
            orientations = [pair[pair_index] for pair in orientations]
            if set([orientation for orientation in orientations if orientation != '']) == {'A'}:
                h_bonds.reverse()
            elif set([orientation for orientation in orientations if orientation != '']) != {'P'}:
                print('ERROR: Strand {} is listed as both antiparallel and '
                      'parallel to strand {}'.format(next_strand, current_strand))
            for h_bonds_index, res in enumerate(h_bonds):
                if float(res) != 0.0 and float(res) in res_list:
                    res_list_index = res_list.index(float(res))
                    break
            index_diff = abs(res_list_index - h_bonds_index)
            for h_bonds_index, res in enumerate(h_bonds):
                res_array[-1, h_bonds_index+index_diff] = dssp_num[h_bonds_index]

            res_list_2 = res_array[-1:, ].tolist()
            res_list_2 = [res for res_sub_list in res_list_2 for res in res_sub_list]

            df = pd.DataFrame(res_array)
            df.to_csv('/Users/ks17361/Documents/Shear_number_calc.csv')

            shear_estimates = []
            for res in dssp_num:
                index_1 = res_list_1.index(float(res))
                index_2 = res_list_2.index(float(res))
                shear_estimate = abs(index_2 - index_1)
                shear_estimates.append(shear_estimate)
            shear = scipy.stats.mode(shear_estimates)
            print(shear_estimates)
            print(shear)
            shear_numbers[domain_id] = shear

            import sys
            sys.exit()


            current_strand = strand_2
            while any(x not in processed_strands for x in G.neighbors(current_strand)):
                next_strand = G.neighbors(current_strand)[0]
                if next_strand in processed_strands:
                    next_strand = G.neighbors(current_strand)[1]
                processed_strands.append(next_strand)

                next_strand_df = sec_struct_df[sec_struct_df['STRAND_NUM']==next_strand]
                dssp_num = next_strand_df['DSSP_NUM'].tolist()
                h_bonds = next_strand_df['H-BONDS'].tolist()
                for h_bonds_index, pair in enumerate(h_bonds):
                    if pair[0] in res_list:
                        res_list_index = res_list.index(pair[0])
                    elif pair[1] in res_list:
                        res_list_index = res_list.index(pair[1])
                    else:
                        continue
                    res_list[res_list_index] = dssp_num[h_bonds_index]
                for residue in dssp_num:
                    if residue not in res_list and residue > min(res_list):
                        res_list.append(residue)

                print(res_list)

                current_strand = next_strand

            shear = len(res_list) - strand_1_df.shape[0]
            print(domain_id)
            print(shear)

            import sys
            sys.exit()

        with open(
            'CATH_{}_resn_{}_rfac{}'.format(self.code, self.resn, self.rfac), 'a'
            ) as unprocessed_file:
            unprocessed_file.write('\n\nBarrel formed from discontinuous sheet:\n')
            for domain_id in unprocessed_list:
                unprocessed_file.write('{}\n'.format(domain_id))

        return shear_numbers
