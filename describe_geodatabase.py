def describe_gdb(gdb, output_folder):
        
    def get_tables_from_GDB():
         for fds in arcpy.ListDatasets('','feature') + ['']:
             for fc in arcpy.ListFeatureClasses('','',fds):
                 yield os.path.join(arcpy.env.workspace, fds, fc)


    def describe_table(table, dest_csv):
        fields = [(field.name,
                   field.aliasName, 
                   field.type,
                   field.length,
                   field.precision,
                   field.scale,
                   field.defaultValue,
                   field.domain,
                   field.editable,
                   field.isNullable,
                   field.required,
                   len(set([row for row in 
                       arcpy.da.SearchCursor(table, field.name)])))
                   for field in arcpy.ListFields(table)]

        with open(dest_csv, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(
                ['NAME', 'ALIAS', 'TYPE', 'LENGTH', 'PRECISION', 'SCALE',
                 'DEFAULT', 'DOMAIN', 'EDITABLE', 'ISNULLABLE', 'REQUIRED',
                 'UNIQUE'])
        
            for field in fields:
                    csvwriter.writerow(field)

    # Set the workspace to gdb
    arcpy.env.workspace = gdb

    # List all the feature classes in gdb
    tables = list(get_tables_from_GDB())

    # Create a list of jobs (feature_class, output_table)    
    jobs = [(table,
             os.path.join(output_folder,
                          'tbl_{}.csv'.format(os.path.basename(table))))
                           for table in tables]

    for job in jobs:
        describe_table(job[0], job[1])

    # Get the domains
    desc = arcpy.Describe(gdb)
    domains = desc.domains

    for domain in domains:
        table = os.path.join(output_folder,
                             'dmn_{}.csv'.format(domain.replace(' ', '_')))
        
        arcpy.DomainToTable_management(gdb, domain, table,
                                       'field', 'description', '#')



