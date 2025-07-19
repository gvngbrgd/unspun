@app.route('/view_code', methods=['GET'])
def view_code():
    """Display the contents of this file in a simple textarea."""
    try:
        with open(__file__, 'r') as f:
            code = f.read()
        # Using a textarea makes it easy for users to copy the source
        html_content = (
            "<textarea style='width:100%; height:90vh;' readonly>" +
            escape(code) +
            "</textarea>"
        )
        return html_content
    except Exception as e:
        return jsonify({"error": str(e)}), 500
