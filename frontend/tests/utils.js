// UTILS
/* Used to convert input to be same as graphology serialization (all strings). */
function convertToArrayOfStrings(matrix) {
  var stringMatrix = [];
  for (var i = 0; i < matrix.length; i++) {
    var stringRow = [];
    for (var j = 0; j < matrix[i].length; j++) {
      stringRow.push(matrix[i][j].toString());
    }
    stringMatrix.push(stringRow);
  }
  return stringMatrix;
}
