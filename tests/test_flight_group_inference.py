from openpyxl import Workbook

from voucher_generator.xlsx_importer import (
    build_merged_lookup,
    build_flight_column_map,
    extract_flight_segments_for_row,
)


def test_merged_flight_groups_infer_direction_and_preserve_duplicate_numbers():
    ws = Workbook().active
    # Same arrangement as the regional Latin Grammys workbook:
    # outgoing flight blocks, hotel divider, return flight blocks.
    groups = [
        (1, "FLIGHT 1 (IDA)", "AA1486", "GUA", "DFW"),
        (8, "FLIGHT 1", "AA2530", "DFW", "LAS"),
        (15, "FLIGHT 2", "AA3000", "LAS", "LAX"),
        (29, "FLIGHT 1", "AA1482", "LAS", "DFW"),
        (36, "FLIGHT 2", "AA2455", "DFW", "GUA"),
    ]
    for start, label, number, origin, destination in groups:
        ws.merge_cells(start_row=2, start_column=start, end_row=2, end_column=start+6)
        ws.cell(2, start, label)
        for offset, header in enumerate(("FLIGHT 1 NUMBER", "FROM", "DATE OF DEPARTURE",
                                         "TIME OF DEPARTURE", "TIME OF ARRIVAL",
                                         "DATE OF ARRIVAL", "AIRPORT DESTINATION")):
            ws.cell(3, start + offset, header)
        ws.cell(4, start, number)
        ws.cell(4, start+1, origin)
        ws.cell(4, start+6, destination)
    ws.merge_cells(start_row=2, start_column=22, end_row=2, end_column=28)
    ws.cell(2, 22, "HOTEL")
    merged = build_merged_lookup(ws)
    mapping = build_flight_column_map(ws, merged, 2, 3)
    assert len(mapping["outbound"]) == 3
    assert len(mapping["return"]) == 2
    flights = extract_flight_segments_for_row(ws, merged, 4, mapping)
    assert [(s["flight_number"], s["destination_airport"]) for s in flights["outbound"]] == [
        ("AA1486", "DFW"), ("AA2530", "LAS"), ("AA3000", "LAX")
    ]
    assert [(s["flight_number"], s["destination_airport"]) for s in flights["return"]] == [
        ("AA1482", "DFW"), ("AA2455", "GUA")
    ]
