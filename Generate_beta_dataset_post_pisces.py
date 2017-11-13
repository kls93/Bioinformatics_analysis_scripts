
import os
import pandas as pd
import random
from Subroutines import beta_structure_coords
prompt = '> '

# Determines whether user wants to analyse beta-barrels or beta-sandwiches
print('Beta-sandwiches or beta-barrels?')
owChoice = input(prompt).lower()
if owChoice in ['beta-barrels', 'barrels']:
    run = '2.40'
elif owChoice in ['beta-sandwiches', 'sandwiches']:
    run = '2.60'
else:
    for char in owChoice:
        if char.isdigit():
            run = owChoice
            break

# Determines the raw file path of the domain descriptions list
print('Provide directory of domains description file')
owChoice = input(prompt)
os.chdir('{}'.format(owChoice))

# Specifies the resolution and Rfactor (working value) cutoffs used in previous
# steps
print('Select resolution cutoff')
resn = float(input(prompt))
print('Select Rfactor (working value) cutoff')
rfac = float(input(prompt))

# Loads the dataframe generated in previous steps
filtered_domain_dict = pd.read_pickle('CATH_{}_resn_{}_rfac_{}_pre_pisces.pkl'.format(run, resn, rfac))
# Loads the list of FASTA sequences generated by the PISCES web server
fasta_list = []
with open('CATH_{}_{}_{}_domain_chain_entries.txt'.format(self.run, self.resn, self.rfac), 'r') as chain_entries_file:
    for seq in chain_entries_file:
        fasta_list.append(seq)

# For each of the sequences returned by the PISCES web server, selects a
# random PDB ID from the filtered dataframe of CATH domains from which to
# select coordinates
pdb_list = []
for seq in fasta_list:
    pdb_sub_list = []
    for row in range(filtered_domain_dict.shape[0]):
        if seq == filtered_domain_dict['DSEQS'][row]:
            pdb_sub_list.append(filtered_domain_dict['PDB_CODE'][row])

    rand_num = random.randint(0, len(pdb_list)-1)
    pdb_id = pdb_sub_list[rand_num]
    pdb_list.append(pdb_id)

# Filters dataframe further to retain only the domains selected in the previous
# step
pisces_domain_dict = filtered_domain_dict.loc[df['PDB_CODE'].isin(pdb_list)]

# Extends the DataFrame to list the xyz coordinates of each segment sequence (SSEQS)
domain_xyz = []
unprocessed_list = []
for row in range(0, pisces_domain_dict.shape[0]):
    print('Downloading {} from the RCSB PDB website'.format(pisces_domain_dict['PDB_CODE'][row]))
    url = 'http://www.rcsb.org/pdb/files/{}.pdb'.format(pisces_domain_dict['PDB_CODE'][row].upper())
    pdb_file_lines = requests.get(url).text
    pdb_file_lines = pdb_file_lines.split('\n')
    pdb_file_lines = [line for line in pdb_file_lines
                      if line[0:6].strip() in ['ATOM', 'HETATM', 'TER']]
    pdb_file_lines.append('TER'.ljust(80))

    for index_1, segment in enumerate(pisces_domain_dict['SSEQS'][row]):
        sequences = []
        indices = []

        start = pisces_domain_dict['SSEQS_START_STOP'][row][index_1][0].replace('START=', '')
        stop = pisces_domain_dict['SSEQS_START_STOP'][row][index_1][1].replace('STOP=', '')
        start_seq = False
        stop_seq = False
        sequence = ''
        index = []

        for index_2, line in enumerate(pdb_file_lines):
            if index_2 != (len(pdb_file_lines)-1):
                if line[22:27].strip() == start and line[21:22] == pisces_domain_dict['CHAIN'][row]:
                    start_seq = True

                if start_seq is True and stop_seq is False:
                    index.append(index_2)
                    if (line[22:27].strip() != pdb_file_lines[index_2+1][22:27].strip()
                        or pdb_file_lines[index_2+1][0:3] == 'TER'):
                            if line[17:20].strip() in amino_acids_dict:
                                sequence = sequence + amino_acids_dict[line[17:20].strip()]
                elif stop_seq is True:
                    sequences.append(sequence)
                    indices.append(index)
                    sequence = ''
                    index = []
                    start_seq = False
                    stop_seq = False
                    continue

                if (pdb_file_lines[index_2+1][0:3] == 'TER'
                    or (line[22:27].strip() == stop
                        and line[21:22] == domain_dict['CHAIN'][row]
                        and pdb_file_lines[index_2+1][22:27].strip() != stop
                        )
                    ):
                        stop_seq = True

        xyz = []
        sequence_identified = False
        for index_3, sequence in enumerate(sequences):
            similarity = SequenceMatcher(a=segment, b=sequence).ratio()
            if similarity > 0.95:
                sequence_identified = True
                for index_4 in indices[index_3]:
                    x = float(pdb_file_lines[index_4][30:38].strip())
                    y = float(pdb_file_lines[index_4][38:46].strip())
                    z = float(pdb_file_lines[index_4][46:54].strip())
                    xyz.append([x, y, z])

            if sequence_identified is True:
                break

        domain_xyz.append(xyz)

        if similarity <= 0.95:
            unprocessed_list.append('{}\n'.format(pisces_domain_dict['PDB_CODE'][row]))

with open('Unprocessed_beta_sandwich_pdbs.txt', 'w') as unprocessed_file:
    for pdb_file in set(unprocessed_list):
        unprocessed_file.write('{}\n'.format(pdb_file))

domain_xyz = pd.DataFrame({'XYZ': domain_xyz})
domain_dict = pd.concat([domain_dict, domain_xyz], axis=1)
domain_dict.to_csv('CATH_2.60_domain_desc_DataFrame_v_4_2_0.csv')
domain_dict.to_pickle('CATH_2.60_domain_desc_DataFrame_v_4_2_0.pkl')
