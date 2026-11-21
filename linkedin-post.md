# LinkedIn post — draft

Most Power BI maps look the same. So I built one that isn't a map at all.

Every coloured tile below is a plain **matrix cell**. No map visual, no shape map,
no custom visual, no Azure Maps — just a grid of cards arranged to look like
Melbourne.

Each card is one suburb, showing the number of reported road crashes from 2021–2025.
The bay is made of empty grid cells. The colours come from a field-value rule on the
matrix values. That's it.

The data is real: 45,893 crashes across 380 suburbs, from Transport Victoria's open
road crash dataset, spatially joined to Vicmap suburb boundaries. Melbourne comes in
at 1,296, Dandenong 610, Epping 598, Preston 578.

What I like about this pattern is that it gives you the readability of a map with the
control of a table: exact numbers, consistent card sizes, accessible labels, and no
geography licensing. It's a good reminder that a "map" in BI is often just a layout
problem, not a mapping problem.

Built and published in Microsoft Fabric with Power BI, with the whole thing assembled
in OpenCode using the Fabric skills.

Live report: https://app.fabric.microsoft.com/groups/6881ccf8-e614-4ab8-b02d-c4820eded362/reports/82d14a19-a8b4-434f-98c3-6fed0e9ee6d5

Source, data and the full project: https://github.com/tauseefau/melbourne-crash-card-map

What's the most interesting non-map "map" you've seen in Power BI?

#PowerBI #MicrosoftFabric #DataVisualization #OpenCode #PowerBIDeveloper #FabricSkills #Melbourne #RoadSafety #DataStorytelling
