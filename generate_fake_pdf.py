# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_fake_building_plan(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, height - 100, "RESIDENTIAL REMODEL PLAN")

    # Details
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 150, "Project Address: 123 Main St, Santa Clara, CA 95050")
    c.drawString(100, height - 170, "Project Type: Single Family Home Addition")
    c.drawString(100, height - 190, "Square Footage: 1,200 sq ft addition")

    # Specifications
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, height - 230, "Specifications:")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 250, "1. HVAC: Install new natural gas furnace (80% AFUE).")
    c.drawString(100, height - 270, "2. Water Heater: Install 50-gallon gas storage water heater.")
    c.drawString(100, height - 290, "3. Lighting: 50% high-efficacy LED lighting, 50% incandescent fixtures.")
    c.drawString(100, height - 310, "4. Framing: 2x4 wood studs at 16 inches on center.")
    c.drawString(100, height - 330, "5. Insulation: R-13 fiberglass batts in exterior walls.")

    # Drawings (Fake)
    c.rect(100, height - 600, 400, 200)
    c.drawString(250, height - 500, "Floor Plan Diagram")

    # Save
    c.save()

if __name__ == "__main__":
    output_path = "sample_building_plan.pdf"
    create_fake_building_plan(output_path)
    print(f"Created fake building plan at: {output_path}")
