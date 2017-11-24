
import os
from Subroutines import select_beta_structures, filter_beta_structure
prompt = '> '

# Determines whether user wants to analyse beta-barrels or beta-sandwiches
print('Beta-sandwiches or beta-barrels?')
structure_type = input(prompt).lower()
if structure_type in ['beta-barrels', 'barrels']:
    run = '2.40'
elif structure_type in ['beta-sandwiches', 'sandwiches']:
    run = '2.60'
else:
    for char in structure_type:
        if char.isdigit():
            run = structure_type
            break

# Determines the absolute file path of the domain descriptions list
print('Provide directory of domains description file')
directory = input(prompt)
os.chdir('{}'.format(directory))

# Generates a list of the domain descriptions provided in
# CATH_domain_description_v_4_2_0.txt. Then filters the domain descriptions
# list for beta-structures (the type dependent upon the earlier user input),
# picking out PDB accession codes and sequences (whose values are stored in the
# 'domain_dict' dataframe).
beta_structure = select_beta_structures(run=run)
domains_description = beta_structure.domain_desc_list()
domain_dict = beta_structure.domain_desc_filter(domains_description)

# Filters the domain_dict for X-ray structures with resolution < 1.6 Angstroms
# (to allow distinction of hydrogen bonds) and R_factor (working value) < 0.20.
# Writes a file listing all PDB ids that meet these criteria suitable for
# uploading to the cd_hit web server.
os.mkdir('CATH_{})'.format(run))
os.chdir('CATH_{})'.format(run))

print('Select resolution cutoff')
resn = float(input(prompt))
print('Select Rfactor (working value) cutoff')
rfac = float(input(prompt))

beta_structure = filter_beta_structure(run=run, resn=resn, rfac=rfac, domain_dict=domain_dict)
filtered_domain_dict = beta_structure.resn_rfac_filter()
beta_structure.gen_cd_hit_list(filtered_domain_dict)
