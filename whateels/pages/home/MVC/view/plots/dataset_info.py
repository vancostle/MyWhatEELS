# Compatibility shim. The implementation now lives in whateels/components/dataset_info_card.py
# because the Fitting page reuses the very same card: there must be ONE implementation so an edit
# made in Home or in Fitting writes to the same dataset.attrs / app_state and can never diverge.
# The four Home plot modules keep importing create_home_dataset_info from here unchanged.
from whateels.components import create_dataset_info_card

create_home_dataset_info = create_dataset_info_card
