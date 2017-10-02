'''
you need to previously define the following:
poly = your input polygon
GCDB = path to the GCDB layer
out_csv = path to save the plss.csv
'''

write_plss = True  # a switch to tie to a tool input parameter

if write_plss = True:
    
    # intersect survey poly with GCDB Survey Grid
    arcpy.Intersect_analysis([poly, GCDB], "in_memory\\plss", "NO_FID")

    # these fields may not match your data field names
    freqFields = ["PLSSID", "FRSTDIVNO", "QQSEC"]
    
    arcpy.Frequency_analysis("in_memory\\plss", "in_memory\\Loc", freqFields)
    
    fieldNames = ["PM", "TWN", "RNG", "SEC", "QQ1", "QQ2"]
    
    plss = []
    
    with arcpy.da.SearchCursor("in_memory\\plss", freqFields) as cursor:
        for row in cursor:
            # these are string slices and may not match your data strings!
            pm  = str(row[0])[2:4]
            twn = str(row[0])[5:7]+str(row[0])[8]
            rng = str(row[0])[10:12]+str(row[0])[13]
            sec = str(row[1])
            qq1 = str(row[2])[0:2]
            qq2 = str(row[2])[2:4]
            
            plss.append([pm, twn, rng, sec, qq1, qq2])
                   
    df = pd.DataFrame(print_list, columns=fieldNames)
    df.to_csv(out_csv, index=False)
