/[:blank:]*#/ { next }  # ignore comments (lines starting with #)
BEGIN { FS = "," }      # set column separator to comma (for CSV files)
NF < 3 { next }         # ignore lines which don't have at least 3 columns
{ print $1, $5 }        # print columns 1 and 5